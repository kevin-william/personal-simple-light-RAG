from tests.test_ingestion import service
from tests.test_pipeline import FakeLLM
from src.rag.pipeline import Pipeline
from types import SimpleNamespace


def test_active_evidence_after_update_and_delete(tmp_path):
    i = service(tmp_path)
    doc = tmp_path/'a.txt'
    doc.write_text('old instructions')
    identifier = i.ingest_file(doc)['id']
    p = Pipeline(i.settings,FakeLLM(),i.embedder,i)
    list(p.stream('q'))
    assert p.last_result.supplied[0].text == 'old instructions'
    doc.write_text('new instructions')
    i.ingest_file(doc)
    list(p.stream('q'))
    assert p.last_result.supplied[0].text == 'new instructions'
    i.delete_source(identifier,True)
    p.sync()
    assert not p.last_result.supplied
    list(p.stream('q'))
    assert not p.last_result.supplied and p.last_result.mode == 'no_evidence'


def test_new_question_never_transforms_previous_answer(tmp_path):
    i = service(tmp_path)
    doc = tmp_path/'a.txt'
    doc.write_text('configuration instructions')
    i.ingest_file(doc)
    p = Pipeline(i.settings,FakeLLM(),i.embedder,i)
    list(p.stream('Assunto exclusivo da primeira pergunta'))
    observed=[]
    i.embedder.encode=lambda texts:observed.extend(texts) or [[1.,0.]]
    list(p.stream('resuma isso'))
    assert observed == ['resuma isso']
    assert p.last_result.mode == 'retrieval'
    assert 'Assunto exclusivo' not in str(p.llm.input)
    assert 'Resposta [1].' not in str(p.llm.input)
    assert p.last_result.summary == ''
    assert p.llm.calls == 2
