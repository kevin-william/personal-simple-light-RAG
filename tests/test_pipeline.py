from types import SimpleNamespace
import pytest
from src.rag.pipeline import Pipeline
from src.rag.query_resolver import Resolution
from src.rag.vectorstore import Hit
from src.config import Settings
from tests.test_ingestion import FakeEmbedder


class FakeLLM:
    def tokens(self,text):
        return len(text)//4 + 1
    def count_messages(self,messages):
        return sum(self.tokens(m['content']) for m in messages)+12
    def stream(self,messages):
        self.input = messages
        yield 'Resposta [1].'
    def complete(self,*args,**kwargs):
        return 'Tema X'


def build(tmp_path,question='OAuth2 no X'):
    s = Settings(root=tmp_path,_env_file=None)
    hit = Hit('v:0','Configuração OAuth2 do X.',{'version':'v','source':'doc'},0.)
    ingest = SimpleNamespace(catalog=SimpleNamespace(generation=1),query=lambda *a:[hit])
    resolver = SimpleNamespace(resolve=lambda *a:Resolution(standalone_query=question,relevant_context='X',needs_retrieval=True))
    return Pipeline(s,FakeLLM(),FakeEmbedder(),ingest,resolver=resolver)


def test_only_independent_query_and_supplied_citations(tmp_path):
    p = build(tmp_path)
    observed = []
    p.embedder.encode = lambda texts: observed.extend(texts) or [[1.,0.]]
    assert ''.join(p.stream('e como configuro isso?')) == 'Resposta [1].'
    assert observed == ['OAuth2 no X']
    assert len(p.last_result.cited) == 1
    assert p.memory.last_message['content'] == 'Resposta [1].'
    assert '[EVIDÊNCIAS DOCUMENTAIS]' in p.llm.input[1]['content']


def test_budget_and_cancel(tmp_path):
    p = build(tmp_path)
    with pytest.raises(ValueError,match='não cabe'):
        list(p.stream('x'*30000))
    generator = p.stream('q')
    next(generator)
    generator.close()
    assert p.memory.last_message is None


def test_invalid_citation_no_evidence_and_clarification(tmp_path):
    p = build(tmp_path)
    p.llm.stream = lambda messages: iter(['wrong [99]'])
    list(p.stream('q'))
    assert p.last_result.warnings and not p.last_result.cited
    p.ingestor.query = lambda *a:[]
    list(p.stream('q'))
    assert p.last_result.mode == 'no_evidence'
    p.resolver.resolve = lambda *a:Resolution(standalone_query='q',relevant_context='',needs_retrieval=True,clarification_needed='Qual produto?')
    assert ''.join(p.stream('q')) == 'Qual produto?'
