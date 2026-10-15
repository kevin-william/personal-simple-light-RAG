from pathlib import Path
import time
from typing import Set

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label, Static, SelectionList
from textual.widgets.selection_list import Selection
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text


CSS = """
Screen {
    background: #090c10;
    color: #e6edf3;
}

#resource-monitor {
    height: 4;
    width: 100%;
    background: #0d1117;
    border: solid #21262d;
    padding: 0 1;
    margin: 0 1;
}

#main-container {
    height: 1fr;
    width: 100%;
    layout: horizontal;
    padding: 1;
}

/* ─── Bloco de Inferência ─── */
#inference-block {
    width: 68%;
    height: 100%;
    border: round #00f0ff;
    background: #0f141c;
    margin-right: 1;
    padding: 1;
}

.block-title-cyan {
    color: #00f0ff;
    text-style: bold;
    padding-bottom: 1;
    border-bottom: solid #1c2736;
}

#chat-scroll {
    height: 1fr;
    background: #07090d;
    border: solid #182230;
    padding: 1;
    margin-bottom: 1;
    scrollbar-color: #00f0ff #0f141c;
}

.chat-msg {
    margin-bottom: 1;
    width: 100%;
}

#prompt-bar {
    height: auto;
    width: 100%;
    layout: horizontal;
    align: left middle;
}

#prompt-input {
    width: 1fr;
    background: #141b24;
    border: tall #26354a;
    color: #ffffff;
}

#prompt-input:focus {
    border: tall #00f0ff;
}

#send-btn {
    width: 16;
    margin-left: 1;
    background: #00f0ff;
    color: #000000;
    text-style: bold;
    border: none;
}

#send-btn:hover {
    background: #70f7ff;
}

/* ─── Bloco de Gestão do RAG ─── */
#rag-block {
    width: 32%;
    height: 100%;
    border: round #ff007f;
    background: #0f141c;
    padding: 1;
}

.block-title-magenta {
    color: #ff007f;
    text-style: bold;
    padding-bottom: 1;
    border-bottom: solid #2c1a2e;
}

#rag-actions-subblock {
    height: auto;
    background: #141a22;
    border: solid #291e2b;
    padding: 1;
    margin-top: 1;
    margin-bottom: 1;
}

#add-doc-btn {
    width: 100%;
    background: #ff007f;
    color: #ffffff;
    text-style: bold;
    border: none;
    margin-bottom: 1;
}

#add-doc-btn:hover {
    background: #ff4da6;
}

#refresh-btn {
    width: 100%;
    background: #1a222e;
    color: #00f0ff;
    border: solid #2a384c;
}

#refresh-btn:hover {
    border: solid #00f0ff;
}

#rag-filter-subblock {
    height: 1fr;
    background: #141a22;
    border: solid #242f3f;
    padding: 1;
}

.sub-title {
    color: #00ff66;
    text-style: bold;
    margin-bottom: 1;
}

#filter-actions-bar {
    height: auto;
    width: 100%;
    layout: horizontal;
    margin-bottom: 1;
}

.filter-btn {
    width: 1fr;
    margin-right: 1;
    background: #18202b;
    color: #9eacba;
    border: solid #263345;
}

.filter-btn:hover {
    color: #00ff66;
    border: solid #00ff66;
}

SelectionList {
    height: 1fr;
    background: #0b0f14;
    border: solid #182230;
    padding: 0 1;
    scrollbar-color: #00ff66 #0f141c;
}

SelectionList:focus {
    border: solid #00ff66;
}

/* ─── Modal de Adicionar Documentos ─── */
AddDocumentModal {
    align: center middle;
}

#modal-dialog {
    width: 70;
    height: auto;
    background: #121822;
    border: thick #ff007f;
    padding: 2;
}

#modal-title {
    color: #ff007f;
    text-style: bold;
    margin-bottom: 1;
}

#modal-input {
    width: 100%;
    margin-bottom: 1;
    background: #0b0e14;
    border: tall #29384d;
    color: #ffffff;
}

#modal-input:focus {
    border: tall #ff007f;
}

#modal-buttons {
    width: 100%;
    layout: horizontal;
    align: right middle;
}

#modal-ingest-btn {
    background: #00ff66;
    color: #000000;
    text-style: bold;
    margin-right: 1;
}

#modal-cancel-btn {
    background: #252e3d;
    color: #ffffff;
}

#modal-status {
    margin-top: 1;
    color: #ffea00;
}
"""


class AddDocumentModal(ModalScreen[bool]):
    def __init__(self, app_instance):
        super().__init__()
        self.rag_app = app_instance

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            yield Label("📁 ADICIONAR ARQUIVO OU PASTA AO RAG", id="modal-title")
            yield Label("Formatos aceitos: PDF com texto, TXT e Markdown (UTF-8).", classes="info-text")
            yield Input(placeholder="Caminho do arquivo ou pasta...", id="modal-input")
            with Horizontal(id="modal-buttons"):
                yield Button("Iniciar Ingestão", id="modal-ingest-btn")
                yield Button("Cancelar", id="modal-cancel-btn")
            yield Label("", id="modal-status")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "modal-cancel-btn":
            self.dismiss(False)
        elif event.button.id == "modal-ingest-btn":
            path_text = self.query_one("#modal-input", Input).value.strip().strip('"')
            if not path_text:
                self.query_one("#modal-status", Label).update("[red]Informe um caminho válido.[/red]")
                return
            self.execute_ingestion(path_text)

    @work(thread=True)
    def execute_ingestion(self, path: str) -> None:
        status_label = self.query_one("#modal-status", Label)
        self.app.call_from_thread(status_label.update, "[yellow]Processando documento(s)...[/yellow]")
        from .ingestion import ingest
        try:
            results = ingest(self.rag_app, path)
            failed = [r for r in results if r.get("status") == "failed"]
            added = len([r for r in results if r.get("status") == "added"])
            updated = len([r for r in results if r.get("status") == "updated"])
            if failed:
                msg = f"[red]Falha em {len(failed)} arquivo(s): {failed[0].get('error')}[/red]"
                self.app.call_from_thread(status_label.update, msg)
            else:
                self.app.call_from_thread(self.dismiss, True)
        except Exception as error:
            self.app.call_from_thread(status_label.update, f"[red]Erro na ingestão: {error}[/red]")


class ResourceMonitorWidget(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_content = ""

    def update_metrics(self, snapshot: dict) -> None:
        cpu = snapshot.get("cpu_percent", 0.0)
        ram_app = snapshot.get("process_rss_mb", 0.0)
        ram_total = snapshot.get("ram_total_gb", 0.0)
        ram_used = snapshot.get("ram_used_gb", 0.0)
        ram_pct = snapshot.get("ram_percent", 0.0)

        line1 = (
            f"[bold #00f0ff]💻 CPU:[/bold #00f0ff] {cpu:.1f}%   │   "
            f"[bold #00f0ff]🧠 RAM:[/bold #00f0ff] {ram_app:.1f} MB (App) / {ram_used:.1f} GB ({ram_pct:.1f}% de {ram_total:.1f} GB)"
        )

        if snapshot.get("gpu_available"):
            vram_pct = snapshot.get("vram_percent", 0.0)
            vram_color = "#00ff66" if vram_pct < 80 else ("#ffea00" if vram_pct < 90 else "#ff3333")
            gpu_str = (
                f"[bold #ff007f]🎮 GPU:[/bold #ff007f] {snapshot.get('gpu_util', 0)}% ({snapshot.get('gpu_name', 'NVIDIA')})   │   "
                f"[bold {vram_color}]🔥 VRAM:[/bold {vram_color}] {snapshot.get('vram_used_mib', 0)} / {snapshot.get('vram_total_mib', 0)} MiB ({vram_pct:.1f}%)   │   "
                f"[bold #ffea00]🌡️ Temp:[/bold #ffea00] {snapshot.get('gpu_temp_c', 0)}°C"
            )
        else:
            gpu_str = "[dim]🎮 GPU: N/A (Modo CPU)[/dim]"

        content = f"{line1}\n{gpu_str}"
        if content != self._last_content:
            self._last_content = content
            self.update(content)


class RagTuiApp(App):
    CSS = CSS
    TITLE = "PSL-RAG"
    SUB_TITLE = ""

    def __init__(self, rag_app):
        super().__init__()
        self.rag = rag_app
        self.selected_source_ids: Set[str] = set()
        self.is_generating = False
        self._monitor_running = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield ResourceMonitorWidget(id="resource-monitor")
        with Container(id="main-container"):
            # ─── Bloco 1: Inferência ───
            with Vertical(id="inference-block"):
                yield Label("⚡ INFERÊNCIA & CHAT LOCAL", classes="block-title-cyan")
                with VerticalScroll(id="chat-scroll"):
                    pass
                with Horizontal(id="prompt-bar"):
                    yield Input(placeholder="Digite sua pergunta aqui e pressione Enter...", id="prompt-input")
                    yield Button("Enviar ➜", id="send-btn")

            # ─── Bloco 2: Gestão do RAG ───
            with Vertical(id="rag-block"):
                yield Label("📁 GESTÃO DO RAG", classes="block-title-magenta")
                # Sub-bloco 1: Ações
                with Vertical(id="rag-actions-subblock"):
                    yield Label("Ações:", classes="sub-title")
                    yield Button("+ Adicionar Arquivo/Pasta", id="add-doc-btn")
                    yield Button("↻ Atualizar Lista", id="refresh-btn")
                # Sub-bloco 2: Checkboxes de seleção
                with Vertical(id="rag-filter-subblock"):
                    yield Label("Fontes Ativas para Busca:", classes="sub-title")
                    with Horizontal(id="filter-actions-bar"):
                        yield Button("Todas", id="select-all-btn", classes="filter-btn")
                        yield Button("Nenhuma", id="select-none-btn", classes="filter-btn")
                    yield SelectionList[str](id="doc-selection-list")
        yield Footer()

    def add_chat_message(self, renderable: str | Static) -> Static:
        chat_scroll = self.query_one("#chat-scroll", VerticalScroll)
        widget = renderable if isinstance(renderable, Static) else Static(renderable, classes="chat-msg")
        chat_scroll.mount(widget)
        chat_scroll.scroll_end(animate=False)
        return widget

    def update_chat_message(self, widget: Static, text: str) -> None:
        chat_scroll = self.query_one("#chat-scroll", VerticalScroll)
        widget.update(text)
        chat_scroll.scroll_end(animate=False)

    def on_mount(self) -> None:
        self.add_chat_message("[bold #00f0ff]Sistema RAG carregado e pronto.[/bold #00f0ff]\n[dim]Selecione os documentos desejados na barra lateral ou faça perguntas para toda a base.[/dim]")
        self.reload_document_checkboxes()
        self._monitor_running = True
        self.run_resource_monitor()

    def reload_document_checkboxes(self) -> None:
        selection_list = self.query_one("#doc-selection-list", SelectionList)
        selection_list.clear_options()

        sources = self.rag.catalog.list_sources()
        if not sources:
            return

        options = []
        for doc in sources:
            name = Path(doc["path"]).name
            label = f"{name} ({doc['chunks']} chunks)"
            options.append(Selection(label, doc["id"], initial_state=True))
        selection_list.add_options(options)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "send-btn":
            self.submit_prompt()
        elif btn_id == "add-doc-btn":
            self.push_screen(AddDocumentModal(self.rag), self.on_modal_close)
        elif btn_id == "refresh-btn":
            self.reload_document_checkboxes()
        elif btn_id == "select-all-btn":
            self.query_one("#doc-selection-list", SelectionList).select_all()
        elif btn_id == "select-none-btn":
            self.query_one("#doc-selection-list", SelectionList).deselect_all()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "prompt-input":
            self.submit_prompt()

    def on_modal_close(self, result: bool) -> None:
        if result:
            self.reload_document_checkboxes()
            self.add_chat_message("[bold #00ff66]Documento(s) adicionados com sucesso ao catálogo.[/bold #00ff66]")

    def submit_prompt(self) -> None:
        if self.is_generating:
            return
        prompt_input = self.query_one("#prompt-input", Input)
        question = prompt_input.value.strip()
        if not question:
            return

        prompt_input.value = ""
        prompt_input.disabled = True
        send_btn = self.query_one("#send-btn", Button)
        send_btn.label = "Gerando..."
        send_btn.disabled = True
        self.is_generating = True

        self.add_chat_message(f"[bold #00f0ff]Você:[/bold #00f0ff] {escape(question)}")
        bot_msg = Static("[bold #ff007f]Assistente:[/bold #ff007f] ", classes="chat-msg")
        self.add_chat_message(bot_msg)

        selection_list = self.query_one("#doc-selection-list", SelectionList)
        selected_ids = list(selection_list.selected)
        active_sources = selected_ids if selected_ids else None
        self.run_rag_stream(question, active_sources, bot_msg)

    @work(thread=True)
    def run_rag_stream(self, question: str, source_ids: list[str] | None, bot_msg: Static) -> None:
        prompt_input = self.query_one("#prompt-input", Input)
        send_btn = self.query_one("#send-btn", Button)

        if not self.rag.catalog.list_sources():
            self.app.call_from_thread(self.update_chat_message, bot_msg, "[yellow]Base vazia. Adicione documentos pelo painel à direita.[/yellow]")
            self.finish_generation(prompt_input, send_btn)
            return

        start_time = time.perf_counter()
        accumulated = ""
        token_count = 0
        try:
            stream = self.rag.pipeline.stream(question, source_ids=source_ids)
            for token in stream:
                accumulated += token
                token_count += 1
                rendered = f"[bold #ff007f]Assistente:[/bold #ff007f] {escape(accumulated)}"
                self.app.call_from_thread(self.update_chat_message, bot_msg, rendered)
            stream.close()

            elapsed = time.perf_counter() - start_time
            answer = self.rag.pipeline.last_result
            final_rendered = f"[bold #ff007f]Assistente:[/bold #ff007f] {escape(accumulated)}"
            # Citações de fontes
            if answer and answer.cited:
                citations_text = f"\n\n[dim #00ff66]Fontes citadas ({len(answer.cited)}):[/dim #00ff66]"
                for i, hit in enumerate(answer.cited, 1):
                    meta = hit.metadata
                    location = f"pág {meta['page']}" if "page" in meta else f"linhas {meta.get('line_start','?')}-{meta.get('line_end','?')}"
                    citations_text += f"\n  [#ff007f][{i}][/#ff007f] [white]{Path(meta.get('source','')).name}[/white] ({location}) - similaridade: {hit.similarity:.4f}"
                final_rendered += citations_text

            if answer and answer.warnings:
                for w in answer.warnings:
                    final_rendered += f"\n[yellow]Aviso: {w}[/yellow]"

            # Tempo do request e taxa de tokens
            tps_str = f" ({token_count / elapsed:.1f} tokens/s)" if token_count > 0 and elapsed > 0 else ""
            final_rendered += f"\n\n[dim #00f0ff]⏱️ Tempo: {elapsed:.2f}s{tps_str}[/dim #00f0ff]"

            self.app.call_from_thread(self.update_chat_message, bot_msg, final_rendered)
        except Exception as error:
            elapsed = time.perf_counter() - start_time
            err_msg = f"[bold #ff007f]Assistente:[/bold #ff007f] {escape(accumulated)}\n[red]Erro durante a inferência ({elapsed:.2f}s): {error}[/red]"
            self.app.call_from_thread(self.update_chat_message, bot_msg, err_msg)
        finally:
            self.finish_generation(prompt_input, send_btn)

    def finish_generation(self, prompt_input: Input, send_btn: Button) -> None:
        def restore():
            prompt_input.disabled = False
            send_btn.label = "Enviar ➜"
            send_btn.disabled = False
            self.is_generating = False
            prompt_input.focus()
        self.app.call_from_thread(restore)

    @work(thread=True)
    def run_resource_monitor(self) -> None:
        import time
        from src.models.hardware import get_resource_snapshot
        try:
            widget = self.query_one("#resource-monitor", ResourceMonitorWidget)
        except Exception:
            return

        while self._monitor_running:
            try:
                snapshot = get_resource_snapshot()
                self.app.call_from_thread(widget.update_metrics, snapshot)
            except Exception:
                pass
            time.sleep(2.0)

    def on_unmount(self) -> None:
        self._monitor_running = False
        from src.models.hardware import get_nvml_client
        client = get_nvml_client()
        if client:
            client.shutdown()

