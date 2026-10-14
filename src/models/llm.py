import json
import re
from .downloader import ModelCache
from .hardware import require_device


def serialize(messages):
    parts = []
    for message in messages:
        if message['role'] not in {'system','user','assistant'}:
            raise ValueError('Papel de mensagem inválido.')
        # Prevent literal document content from becoming a special token.
        content = message['content'].replace('<|','< |')
        parts.append(f'<|{message["role"]}|>{content}<|end|>')
    return ''.join(parts) + '<|assistant|>'


class LLM:
    def __init__(self, settings, factory=None):
        self.settings, self.factory = settings, factory
        self.model = None
        self.verified = False
        self.offload_effective = None
        self._callback = None

    def load(self):
        if hasattr(self, 'before_load'):
            self.before_load()
        if self.model is not None:
            return self.model
        kwargs = dict(n_ctx=self.settings.context_size, n_gpu_layers=self.settings.n_gpu_layers,
                      verbose=False, seed=42)
        if self.factory:
            self.model = self.factory(**kwargs)
            return self.model
        require_device(self.settings, 'llm')
        cache = ModelCache(self.settings)
        directory = cache.verify('llm', full=not self.verified)
        self.verified = True
        import llama_cpp
        from llama_cpp.llama_chat_format import ChatFormatterResponse, chat_formatter_to_chat_completion_handler
        def formatter(*, messages, **options):
            return ChatFormatterResponse(prompt=serialize(messages), stop=['<|end|>','<|endoftext|>'], added_special=True)
        def log(level, text, data):
            line = text.decode('utf-8',errors='replace')
            match = re.search(r'offloaded (\d+)/(\d+) layers to GPU',line)
            if match:
                self.offload_effective = {'layers':int(match[1]), 'total_layers':int(match[2])}
        self._callback = llama_cpp.llama_log_callback(log)
        llama_cpp.llama_log_set(self._callback,None)
        try:
            self.model = llama_cpp.Llama(model_path=str(directory / self.settings.model_filename),
                         chat_handler=chat_formatter_to_chat_completion_handler(formatter), **kwargs)
        except (ValueError, RuntimeError) as error:
            raise RuntimeError('Falha ao carregar Phi-4-mini. Verifique cache/backend, VRAM, offload parcial ou perfil CPU. '+str(error)) from error
        # Explicit official formatter overrides inconsistent GGUF metadata.
        self.template_metadata = self.model.metadata.get('tokenizer.chat_template')
        if self.settings.llm_backend == 'cpu':
            self.offload_effective = {'layers':0, 'total_layers':None}
        elif self.offload_effective and self.offload_effective['layers'] == 0:
            self.unload()
            raise RuntimeError('CUDA configurado mas nenhuma camada foi offloaded. Escolha CPU explicitamente.')
        return self.model

    def unload(self):
        if self.model is not None:
            self.model.close()
            self.model = None

    def tokens(self, text):
        return len(self.load().tokenize(text.encode('utf-8'), add_bos=False, special=True))

    def count_messages(self, messages):
        return self.tokens(serialize(messages))

    def complete(self, messages, max_tokens=None, schema=None):
        limit = max_tokens or self.settings.max_response_tokens
        if self.count_messages(messages) + limit + 32 > self.settings.context_size:
            raise ValueError('Entrada longa demais para a LLM; reduza a pergunta/contexto.')
        options = {'response_format': {'type':'json_object','schema':schema}} if schema else {}
        result = self.load().create_chat_completion(messages=messages, max_tokens=limit, temperature=0.1, **options)
        if result['choices'][0].get('finish_reason') == 'length':
            raise ValueError('Resposta excedeu limite de tokens; aumente o limite configurado.')
        return result['choices'][0]['message']['content'] or ''

    def structured(self, messages, schema, max_tokens=None):
        return json.loads(self.complete(messages,max_tokens,schema))

    def stream(self, messages, max_tokens=None):
        limit = max_tokens or self.settings.max_response_tokens
        if self.count_messages(messages) + limit + 32 > self.settings.context_size:
            raise ValueError('Prompt não cabe no contexto da LLM.')
        iterator = self.load().create_chat_completion(messages=messages, max_tokens=limit,
                                                      temperature=0.1, stream=True)
        try:
            for item in iterator:
                content = item['choices'][0].get('delta',{}).get('content','')
                if content:
                    yield content
        finally:
            if hasattr(iterator,'close'):
                iterator.close()
