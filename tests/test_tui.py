import pytest
from types import SimpleNamespace
from src.ui.tui import RagTuiApp
from textual.widgets import Button, Checkbox, Input, SelectionList, Static
from textual.containers import VerticalScroll
from tests.test_pipeline import build


@pytest.mark.anyio
async def test_tui_layout_and_components(tmp_path):
    pipeline = build(tmp_path)
    mock_sources = [
        {'id': 'src_1', 'path': 'C:/docs/manual.pdf', 'chunks': 10, 'version': 'v1'},
        {'id': 'src_2', 'path': 'C:/docs/notes.txt', 'chunks': 5, 'version': 'v2'}
    ]
    catalog = SimpleNamespace(list_sources=lambda: mock_sources)
    rag_app = SimpleNamespace(pipeline=pipeline, catalog=catalog)

    app = RagTuiApp(rag_app)
    async with app.run_test(size=(140, 50)) as pilot:
        # Verifica a existência dos dois blocos principais
        assert app.query_one('#inference-block') is not None
        assert app.query_one('#rag-block') is not None

        # Verifica widgets do bloco de inferência
        assert app.query_one('#chat-scroll', VerticalScroll) is not None
        prompt_input = app.query_one('#prompt-input', Input)
        send_btn = app.query_one('#send-btn', Button)
        assert prompt_input is not None
        assert send_btn is not None

        # Envia prompt e testa streaming em fluxo contínuo (sem quebra de linha por token)
        prompt_input.value = "Qual a profissão de Iara?"
        await pilot.click(send_btn)
        # Aguarda a finalização do streaming
        for _ in range(30):
            await pilot.pause(0.1)
            if not app.is_generating:
                break

        scroll = app.query_one('#chat-scroll', VerticalScroll)
        chat_msgs = list(scroll.query(Static))
        # Verifica que o assistente gerou mensagem contínua
        assistant_msgs = [m for m in chat_msgs if "Assistente:" in str(m.render())]
        assert len(assistant_msgs) == 1
        # O texto do assistente contém a resposta completa no mesmo widget com indicador de tempo
        rendered_content = str(assistant_msgs[0].render())
        assert "Assistente:" in rendered_content
        assert "Tempo:" in rendered_content

        # Verifica sub-blocos do RAG
        assert app.query_one('#rag-actions-subblock') is not None
        assert app.query_one('#add-doc-btn', Button) is not None
        assert app.query_one('#rag-filter-subblock') is not None

        # Verifica SelectionList de fontes
        sl = app.query_one('#doc-selection-list', SelectionList)
        assert sl is not None
        assert set(sl.selected) == {'src_1', 'src_2'}

        # Testa botão "Nenhuma"
        select_none = app.query_one('#select-none-btn', Button)
        await pilot.click(select_none)
        await pilot.pause()
        assert sl.selected == []

        # Testa botão "Todas"
        select_all = app.query_one('#select-all-btn', Button)
        await pilot.click(select_all)
        await pilot.pause()
        assert set(sl.selected) == {'src_1', 'src_2'}

        # Testa botão de atualizar lista (garante que não dá DuplicateIds)
        refresh_btn = app.query_one('#refresh-btn', Button)
        await pilot.click(refresh_btn)
        await pilot.pause()
        await pilot.click(refresh_btn)
        await pilot.pause()
        assert set(sl.selected) == {'src_1', 'src_2'}


def test_ingestor_and_pipeline_source_ids_filtering(tmp_path):
    pipeline = build(tmp_path)
    # Stream com source_ids não quebra
    tokens = list(pipeline.stream('Pergunta teste', source_ids=['fake']))
    assert len(tokens) > 0

    # Teste no Ingestor real
    from src.config import Settings
    from src.rag.catalog import Catalog
    from src.rag.ingestion import Ingestor
    from src.rag.vectorstore import VectorStore
    from tests.test_ingestion import FakeEmbedder

    settings = Settings(root=tmp_path, chroma_persist_dir=tmp_path/'chroma', _env_file=None)
    catalog = Catalog(tmp_path/'catalog.db')
    store = VectorStore(settings)
    ingestor = Ingestor(settings, catalog, store, FakeEmbedder())
    hits = ingestor.query([0.1]*1024, k=4, source_ids=['fake_id'])
    assert hits == []


def test_catalog_thread_safety(tmp_path):
    import threading
    from src.rag.catalog import Catalog
    catalog = Catalog(tmp_path / 'thread_test.db')
    catalog.stage('v1', 'hash1', 'fp1', 1)
    catalog.activate('v1', 'path1.txt')

    result = []
    errors = []
    def worker():
        try:
            sources = catalog.list_sources()
            result.append(len(sources))
        except Exception as e:
            errors.append(e)

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert not errors
    assert result == [1]
