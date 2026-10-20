import json
import re
from copy import deepcopy
from .downloader import ModelCache
from .hardware import require_device,configure_windows_dlls
from ..metrics import measured


def serialize(messages):
    parts = []
    for message in messages:
        if message['role'] not in {'system','user','assistant'}:
            raise ValueError('Papel de mensagem inválido.')
        # Prevent literal document content from becoming a special token.
        content = message['content'].replace('<|','< |')
        parts.append(f'<|{message["role"]}|>{content}<|end|>')
    return ''.join(parts) + '<|assistant|>'


def native_schema(schema):
    # llama.cpp expands bounded string repetitions into huge grammars.
    # Length remains bounded by generation tokens and the Pydantic validator.
    result = deepcopy(schema)
    def visit(value):
        if isinstance(value,dict):
            value.pop('maxLength',None)
            if value.get('minLength',0)>32:
                value.pop('minLength',None)
            for child in value.values():
                visit(child)
        elif isinstance(value,list):
            for child in value:
                visit(child)
    visit(result)
    return result


class LLM:
    def __init__(self, settings, factory=None):
        self.settings, self.factory = settings, factory
        self.model = None
        self.verified = False
        self.offload_effective = None
        self._callback = None
        self.truncated = False
        self.last_completion_truncated = False
        self.load_log = []
        self.native_timings = {}

    @measured('llm_load',lambda self:self.model is None)
    def load(self):
        if hasattr(self, 'before_load'):
            self.before_load()
        if self.model is not None:
            return self.model
        kwargs = dict(n_ctx=self.settings.context_size, n_gpu_layers=self.settings.n_gpu_layers,
                      n_batch=min(self.settings.llm_batch_size,self.settings.context_size),
                      n_ubatch=min(self.settings.llm_batch_size,self.settings.context_size),verbose=False, seed=42)
        if self.factory:
            self.model = self.factory(**kwargs)
            return self.model
        require_device(self.settings, 'llm')
        cache = ModelCache(self.settings)
        directory = cache.verify('llm', full=not self.verified)
        self.verified = True
        configure_windows_dlls()
        try:
            import llama_cpp
            if hasattr(llama_cpp, '_utils') and hasattr(llama_cpp._utils, 'suppress_stdout_stderr'):
                llama_cpp._utils.suppress_stdout_stderr.__enter__ = lambda self: self
                llama_cpp._utils.suppress_stdout_stderr.__exit__ = lambda self, *args: None
        except (ImportError,OSError,RuntimeError) as error:
            raise RuntimeError('Bibliotecas nativas indisponíveis. Execute scripts/setup.ps1 para o perfil escolhido; não é necessário compilar C++. '+str(error)) from error
        from llama_cpp.llama_chat_format import ChatFormatterResponse, chat_formatter_to_chat_completion_handler
        def formatter(*, messages, **options):
            return ChatFormatterResponse(prompt=serialize(messages), stop=['<|end|>','<|endoftext|>'], added_special=True)
        def log(level, text, data):
            line = text.decode('utf-8',errors='replace')
            self.load_log.append(line)
            self.load_log = self.load_log[-64:]
            match = re.search(r'offloaded (\d+)/(\d+) layers to GPU',line)
            if match:
                self.offload_effective = {'layers':int(match[1]), 'total_layers':int(match[2])}
        self._callback = llama_cpp.llama_log_callback(log)
        llama_cpp.llama_log_set(self._callback,None)
        self.offload_effective = None
        self.load_log = []
        try:
            self.model = llama_cpp.Llama(model_path=str(directory / self.settings.model_filename),
                         chat_handler=chat_formatter_to_chat_completion_handler(formatter), **kwargs)
        except (ValueError, RuntimeError, MemoryError) as error:
            self.unload()
            detail = ''.join(self.load_log[-6:])
            raise RuntimeError(f'Falha ao carregar Phi-4-mini em {self.settings.llm_backend}. Verifique cache, contexto/VRAM ou selecione --profile cpu. '+str(error)+' '+detail) from error
        # Explicit official formatter overrides inconsistent GGUF metadata.
        self.template_metadata = self.model.metadata.get('tokenizer.chat_template')
        markers = ['<|system|>','<|user|>','<|assistant|>','<|end|>']
        identifiers = [self.model.tokenize(t.encode(),add_bos=False,special=True) for t in markers]
        if any(len(ids)!=1 for ids in identifiers) or len({ids[0] for ids in identifiers})!=4:
            self.unload()
            raise RuntimeError('GGUF incompatível com os tokens oficiais do Phi-4-mini.')
        if self.settings.llm_backend == 'cpu':
            self.offload_effective = {'layers':0, 'total_layers':None}
        elif not self.offload_effective or self.offload_effective['layers'] == 0:
            self.unload()
            raise RuntimeError('CUDA configurado mas o offload de camadas não foi confirmado. Escolha --profile cpu explicitamente.')
        return self.model

    def unload(self):
        if self.model is not None:
            model,self.model = self.model,None
            model.close()

    def tokens(self, text):
        return len(self.load().tokenize(text.encode('utf-8'), add_bos=False, special=True))

    def count_messages(self, messages):
        return self.tokens(serialize(messages))

    def complete(self, messages, max_tokens=None, schema=None,allow_truncated=False):
        limit = max_tokens or self.settings.max_response_tokens
        if self.count_messages(messages) + limit + 32 > self.settings.context_size:
            raise ValueError('Entrada longa demais para a LLM; reduza a pergunta/contexto.')
        options = {'response_format': {'type':'json_object','schema':native_schema(schema)}} if schema else {}
        result = self.load().create_chat_completion(messages=messages, max_tokens=limit, temperature=0.1, **options)
        self.last_completion_truncated = result['choices'][0].get('finish_reason') == 'length'
        if self.last_completion_truncated and not allow_truncated:
            raise ValueError('Resposta excedeu limite de tokens; aumente o limite configurado.')
        return result['choices'][0]['message']['content'] or ''

    def structured(self, messages, schema, max_tokens=None):
        return json.loads(self.complete(messages,max_tokens,schema))

    def perf_snapshot(self):
        if self.factory or self.model is None:
            return None
        try:
            import llama_cpp
            data = llama_cpp.llama_perf_context(self.model._ctx.ctx)
            return {name:getattr(data,name) for name in ('t_p_eval_ms','t_eval_ms','n_p_eval','n_eval')}
        except (AttributeError,RuntimeError):
            return None

    def stream(self, messages, max_tokens=None):
        self.truncated = False
        self.native_timings = {}
        limit = max_tokens or self.settings.max_response_tokens
        if self.count_messages(messages) + limit + 32 > self.settings.context_size:
            raise ValueError('Prompt não cabe no contexto da LLM.')
        model = self.load()
        if not self.factory:
            model._ctx.reset_timings()
        iterator = model.create_chat_completion(messages=messages, max_tokens=limit,
                                                      temperature=0.1, stream=True)
        before = self.perf_snapshot()
        try:
            for item in iterator:
                if item['choices'][0].get('finish_reason') == 'length':
                    self.truncated = True
                content = item['choices'][0].get('delta',{}).get('content','')
                if content:
                    yield content
        finally:
            if hasattr(iterator,'close'):
                iterator.close()
            after = self.perf_snapshot()
            if before is not None and after is not None:
                def change(name):
                    return after[name]-before[name] if after[name]>=before[name] else after[name]
                prompt_s,decode_s = change('t_p_eval_ms')/1000,change('t_eval_ms')/1000
                decoded = change('n_eval')
                self.native_timings = {'prompt_eval_seconds':prompt_s,'decode_seconds':decode_s,
                    'prompt_eval_tokens':change('n_p_eval'),'decode_tokens':decoded,
                    'decode_tokens_per_second':decoded/decode_s if decode_s>0 else None}
