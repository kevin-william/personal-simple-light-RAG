from io import StringIO
from types import SimpleNamespace
from rich.console import Console
from src.ui.ingestion import remove,reset,ingest
from src.ui.menu import menu


def test_confirmation_and_file_reports():
    calls = []
    service = SimpleNamespace(delete_source=lambda *a,**k:calls.append('delete') or {'removed':True},
        reset=lambda **k:calls.append('reset') or {})
    app = SimpleNamespace(ingestor=service)
    out = Console(file=StringIO(),force_terminal=False)
    assert not remove(app,'id',lambda _: 'não',out) and not calls
    assert remove(app,'id',lambda _: 'SIM',out)
    assert reset(app,lambda _:'RESET',out)
    assert calls == ['delete','reset']
    service.ingest_path = lambda path,progress:[{'status':'failed','path':path,'error':'bad UTF8'}]
    result = ingest(app,'dir with spaces',out)
    assert result[0]['status']=='failed' and 'bad UTF8' in out.file.getvalue()


def test_list_menu_does_not_load_models():
    stream = StringIO()
    app = SimpleNamespace(catalog=SimpleNamespace(list_sources=lambda:[]))
    commands = iter(['3','0'])
    menu(app,lambda _:next(commands),Console(file=stream))
    assert 'Documentos indexados' in stream.getvalue()
