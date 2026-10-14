from io import StringIO
from types import SimpleNamespace
from rich.console import Console
from src.ui.chat import chat,respond
from tests.test_pipeline import build


def test_stream_clear_and_sources(tmp_path):
    pipeline = build(tmp_path)
    app = SimpleNamespace(pipeline=pipeline,_pipeline=pipeline,catalog=SimpleNamespace(list_sources=lambda:[{}]))
    commands = iter(['question','/sources','/clear','/exit'])
    output = StringIO()
    chat(app,lambda _:next(commands),Console(file=output,width=100))
    assert 'Resposta' in output.getvalue() and 'Memória limpa' in output.getvalue()
    assert pipeline.memory.last_message is None


def test_empty_base_does_not_load_model():
    output = StringIO()
    app = SimpleNamespace(catalog=SimpleNamespace(list_sources=lambda:[]))
    assert respond(app,'q',Console(file=output)) is None
    assert 'Base vazia' in output.getvalue()
