from types import SimpleNamespace
import pytest
from src.rag.pipeline import Pipeline
from src.rag.vectorstore import Hit
from src.config import Settings
from tests.test_ingestion import FakeEmbedder


class FakeLLM:
    def __init__(self):
        self.calls = 0

    def tokens(self,text):
        return len(text)//4 + 1
    def count_messages(self,messages):
        return sum(self.tokens(m['content']) for m in messages)+12
    def stream(self,messages):
        self.input = messages
        self.calls += 1
        yield 'Resposta [1].'
    def complete(self,*args,**kwargs):
        return 'Tema X'
    def structured(self,messages,*args,**kwargs):
        raise AssertionError('Consultas independentes não fazem chamadas estruturadas.')


def build(tmp_path,question='OAuth2 no X'):
    s = Settings(root=tmp_path,_env_file=None)
    hit = Hit('v:0','Configuração OAuth2 do X.',{'version':'v','source':'doc'},0.)
    ingest = SimpleNamespace(catalog=SimpleNamespace(generation=1),query=lambda *a:[hit])
    return Pipeline(s,FakeLLM(),FakeEmbedder(),ingest)


def test_only_independent_query_and_supplied_citations(tmp_path):
    p = build(tmp_path)
    observed = []
    p.embedder.encode = lambda texts: observed.extend(texts) or [[1.,0.]]
    assert ''.join(p.stream('e como configuro isso?')) == 'Resposta [1].'
    assert observed == ['e como configuro isso?']
    assert len(p.last_result.cited) == 1
    assert p.llm.calls == 1 and p.last_result.summary == ''
    assert '[EVIDÊNCIAS DOCUMENTAIS]' in p.llm.input[1]['content']


def test_budget_and_cancel(tmp_path):
    p = build(tmp_path)
    with pytest.raises(ValueError,match='não cabe'):
        list(p.stream('x'*30000))
    generator = p.stream('q')
    next(generator)
    generator.close()
    assert p.last_result.model_text == 'Resposta [1].'
    assert 'interrompida' in p.last_result.warnings[0]
    list(p.stream('nova pergunta'))


def test_invalid_citation_and_no_evidence(tmp_path):
    p = build(tmp_path)
    p.llm.stream = lambda messages: iter(['wrong [99]'])
    list(p.stream('q'))
    assert p.last_result.warnings and not p.last_result.cited
    p.ingestor.query = lambda *a:[]
    list(p.stream('q'))
    assert p.last_result.mode == 'no_evidence'
    assert p.last_result.metrics['llm_calls'] == 0
    assert p.last_result.metrics['generated_tokens'] == 0
    assert p.last_result.metrics['llama_native'] == {}


def test_exact_code_quote_gets_traceable_source(tmp_path):
    p = build(tmp_path)
    command = 'powershell -File setup.ps1 -Profile cpu'
    p.ingestor.query = lambda *a:[Hit('v:0',f'Execute `{command}`.',{'version':'v','source':'doc'},0.)]
    p.llm.stream = lambda messages:iter([f'`{command}`'])
    text = ''.join(p.stream('setup?'))
    assert text.endswith('[1]') and p.last_result.cited[0].id=='v:0'
    assert p.last_result.model_text==f'`{command}`'
