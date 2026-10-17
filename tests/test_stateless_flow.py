from concurrent.futures import ThreadPoolExecutor
import pytest
from tests.test_pipeline import build,FakeLLM
from tests.test_ingestion import service
from src.rag.pipeline import Pipeline


def test_empty_question_and_empty_sources_do_not_load_models(tmp_path):
    p=build(tmp_path)
    p.embedder.encode=lambda *a:(_ for _ in ()).throw(AssertionError('embedding desnecessário'))
    p.llm.tokens=lambda *a:(_ for _ in ()).throw(AssertionError('LLM desnecessária'))
    with pytest.raises(ValueError,match='vazia'):
        list(p.stream('  '))
    list(p.stream('q',source_ids=[]))
    assert p.last_result.mode == 'no_evidence'
    assert p.last_result.metrics['llm_calls'] == 0
    assert p.last_result.metrics['generated_tokens'] == 0


def test_stream_holds_gate_and_releases_on_cancel(tmp_path):
    ingest=service(tmp_path)
    document=tmp_path/'doc.txt'
    document.write_text('instructions')
    identifier=ingest.ingest_file(document)['id']
    p=Pipeline(ingest.settings,FakeLLM(),ingest.embedder,ingest)
    active=p.stream('question')
    next(active)
    result=p.last_result
    # Reject interleaved generators even on the same thread.
    with pytest.raises(RuntimeError,match='andamento'):
        next(p.stream('other question'))
    assert p.last_result is result
    with pytest.raises(RuntimeError,match='andamento'):
        ingest.delete_source(identifier,True)
    with ThreadPoolExecutor() as executor:
        future=executor.submit(ingest.ingest_file,document)
        with pytest.raises(RuntimeError,match='andamento'):
            future.result(timeout=2)
    active.close()
    assert ingest.ingest_file(document)['status']=='skipped'
    list(p.stream('another question'))
    assert p.last_result.metrics['llm_calls']==1


def test_generation_failure_releases_gate_and_closes_iterator(tmp_path):
    p=build(tmp_path)
    closed=[]
    def broken(messages):
        try:
            yield 'parcial'
            raise RuntimeError('native failure')
        finally:
            closed.append(True)
    p.llm.stream=broken
    with pytest.raises(RuntimeError,match='native failure'):
        list(p.stream('q'))
    assert closed and p.last_result.model_text=='parcial'
    assert p.last_result.metrics['llm_calls']==1
    p.clear_memory()
    assert not p.last_result.text


def test_no_history_and_no_auxiliary_calls(tmp_path):
    p=build(tmp_path)
    observed=[]
    p.embedder.encode=lambda texts:observed.extend(texts) or [[1.,0.]]
    for question in ['segredo exclusivo da pergunta A','assunto B','resuma isso']:
        list(p.stream(question))
        assert p.last_result.metrics['llm_calls']==1
        assert 'resolution' not in p.last_result.metrics['phase_seconds']
        assert 'summary' not in p.last_result.metrics['phase_seconds']
    assert observed==['segredo exclusivo da pergunta A','assunto B','resuma isso']
    assert 'segredo exclusivo' not in str(p.llm.input)
    assert 'assunto B' not in str(p.llm.input)
    assert p.llm.calls==3


def test_ingestion_progress_cannot_start_a_query(tmp_path):
    from src.operations import OperationGate
    gate=OperationGate()
    with gate.operation('write'):
        with gate.operation('write'):
            with pytest.raises(RuntimeError,match='andamento'):
                with gate.operation('query'):
                    pytest.fail('Consulta concorrente foi aceita')
    with gate.operation('query'):
        pass


def test_native_close_error_still_finishes_metrics(tmp_path):
    p=build(tmp_path)
    def broken_close(messages):
        try:
            yield 'parcial'
        finally:
            raise RuntimeError('close failed')
    p.llm.stream=broken_close
    iterator=p.stream('q')
    next(iterator)
    with pytest.raises(RuntimeError,match='close failed'):
        iterator.close()
    assert p.metrics._stop.is_set()
    assert p.last_result.metrics['llm_calls']==1
    p.clear_memory()


def test_close_failure_still_releases_storage_lock(tmp_path):
    from src.application import Application
    from src.config import Settings
    from types import SimpleNamespace
    app=Application(Settings(root=tmp_path,_env_file=None))
    cleaned=[]
    app.lifecycle.close=lambda:(_ for _ in ()).throw(RuntimeError('close failed'))
    app._catalog=SimpleNamespace(close=lambda:cleaned.append('catalog'))
    app._lock=SimpleNamespace(release=lambda:cleaned.append('lock'))
    with pytest.raises(RuntimeError,match='close failed'):
        app.close()
    assert cleaned==['catalog','lock']
    assert app._lock is None
