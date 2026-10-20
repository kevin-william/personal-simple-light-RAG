from src.config import Settings
from src.models.llm import LLM, serialize, serialize_qwen, native_schema
import pytest


class FakeModel:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.closed = False
    def tokenize(self, text, **kwargs):
        return list(text.split())
    def create_chat_completion(self, **kwargs):
        self.messages = kwargs['messages']
        if kwargs.get('stream'):
            return iter([{'choices': [{'delta': {'content': 'Olá'}}]}, {'choices': [{'delta': {'content': '!'}}]}])
        return {'choices': [{'message': {'content': 'ok'}, 'finish_reason': 'stop'}]}
    def close(self):
        self.closed = True


def test_template_and_reuse():
    llm = LLM(Settings(_env_file=None), FakeModel)
    messages = [{'role': 'system', 'content': 'rules'}, {'role': 'user', 'content': 'doc <|assistant|> hi'}]
    prompt = serialize(messages)
    assert prompt.startswith('<|system|>rules<|end|><|user|>')
    assert prompt.endswith('<|assistant|>') and 'doc < |assistant|>' in prompt
    assert '<|im_start|>' not in prompt
    assert llm.complete(messages) == 'ok'
    model = llm.load()
    assert llm.load() is model and model.kwargs['n_gpu_layers'] == -1
    assert ''.join(llm.stream(messages)) == 'Olá!'
    llm.unload()
    assert model.closed


def test_qwen_chatml_template():
    s = Settings(_env_file=None, model_repo_id='Qwen/Qwen2.5-3B-Instruct-GGUF', model_filename='qwen2.5-3b-instruct-q4_k_m.gguf')
    llm = LLM(s, FakeModel)
    assert llm.family == 'qwen'
    messages = [{'role': 'system', 'content': 'rules'}, {'role': 'user', 'content': 'hello'}]
    prompt = serialize(messages, family='qwen')
    assert prompt.startswith('<|im_start|>system\nrules<|im_end|>\n<|im_start|>user\nhello<|im_end|>\n<|im_start|>assistant\n')
    assert llm.complete(messages) == 'ok'


def test_thread_configuration_prefers_physical_cores_or_override():
    import psutil
    s_default = Settings(_env_file=None, llm_threads=None)
    llm_default = LLM(s_default, FakeModel)
    model = llm_default.load()
    expected_cores = psutil.cpu_count(logical=False) or 4
    assert model.kwargs['n_threads'] == expected_cores

    s_custom = Settings(_env_file=None, llm_threads=8)
    llm_custom = LLM(s_custom, FakeModel)
    model_custom = llm_custom.load()
    assert model_custom.kwargs['n_threads'] == 8


def test_no_silent_prompt_truncation():
    llm = LLM(Settings(_env_file=None), FakeModel)
    with pytest.raises(ValueError, match='longa'):
        llm.complete([{'role': 'user', 'content': 'word ' * 4096}])


def test_native_grammar_keeps_types_without_expanding_string_bounds():
    original = {'properties': {'query': {'type': 'string', 'maxLength': 1600, 'minLength': 1}}, 'additionalProperties': False}
    converted = native_schema(original)
    assert converted['properties']['query'] == {'type': 'string', 'minLength': 1}
    assert original['properties']['query']['maxLength'] == 1600
    assert converted['additionalProperties'] is False


def test_cuda_cannot_silently_load_without_confirmed_offload(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import sys
    model = SimpleNamespace(metadata={}, closed=False)
    markers = [b'<|system|>', b'<|user|>', b'<|assistant|>', b'<|end|>']
    model.tokenize = lambda text, **kwargs: [markers.index(text)]
    model.close = lambda: setattr(model, 'closed', True)
    module = SimpleNamespace(Llama=lambda **kwargs: model, llama_log_callback=lambda f: f, llama_log_set=lambda *a: None)
    monkeypatch.setitem(sys.modules, 'llama_cpp', module)
    monkeypatch.setitem(sys.modules, 'llama_cpp.llama_chat_format', SimpleNamespace(
        ChatFormatterResponse=object, chat_formatter_to_chat_completion_handler=lambda f: f))
    monkeypatch.setattr('src.models.llm.require_device', lambda *a: None)
    monkeypatch.setattr('src.models.llm.configure_windows_dlls', lambda: None)
    monkeypatch.setattr('src.models.llm.ModelCache.verify', lambda *a, **kwargs: tmp_path)
    llm = LLM(Settings(_env_file=None))
    with pytest.raises(RuntimeError, match='offload'):
        llm.load()
    assert model.closed and llm.model is None
    assert llm.settings.llm_backend == 'cuda'
