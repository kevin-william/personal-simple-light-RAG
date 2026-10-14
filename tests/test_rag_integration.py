from tests.test_ingestion import service
from tests.test_pipeline import FakeLLM
from src.rag.pipeline import Pipeline
from src.rag.query_resolver import Resolution
from types import SimpleNamespace


def test_active_evidence_after_update_and_delete(tmp_path):
    i = service(tmp_path)
    doc = tmp_path/'a.txt'
    doc.write_text('old instructions')
    identifier = i.ingest_file(doc)['id']
    resolver = SimpleNamespace(resolve=lambda *a:Resolution(standalone_query='instructions',relevant_context='',needs_retrieval=True))
    p = Pipeline(i.settings,FakeLLM(),i.embedder,i,resolver=resolver)
    list(p.stream('q'))
    assert p.last_result.supplied[0].text == 'old instructions'
    doc.write_text('new instructions')
    i.ingest_file(doc)
    list(p.stream('q'))
    assert p.last_result.supplied[0].text == 'new instructions'
    i.delete_source(identifier,True)
    list(p.stream('q'))
    assert not p.last_result.supplied and p.last_result.mode == 'no_evidence'
