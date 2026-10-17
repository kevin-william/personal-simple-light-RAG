from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text
import time
from .console import console,show_sources,format_metrics


def respond(app,question,out=console,details=False):
    if not app.catalog.list_sources():
        out.print('Base vazia. Adicione documentos pelo menu ou --add.')
        return None
    stream = app.pipeline.stream(question)
    text = ''
    try:
        with Live(Text('Buscando evidências…'),console=out,refresh_per_second=10) as live:
            last_render = time.monotonic()
            try:
                for token in stream:
                    text += token
                    now = time.monotonic()
                    if now-last_render >= .1:
                        live.update(Markdown(text))
                        last_render = now
            finally:
                live.update(Markdown(text),refresh=True)
    finally:
        stream.close()
    answer = app.pipeline.last_result
    out.print(format_metrics(answer.metrics),style='dim',markup=False)
    for warning in answer.warnings:
        out.print(warning,style='yellow',markup=False)
    if details:
        show_sources(answer,out)
    else:
        out.print(f'{len(answer.cited)} fontes citadas. /sources exibe detalhes.',style='dim')
    return answer


def _default_ask():
    try:
        from prompt_toolkit import PromptSession
        session = PromptSession()
        def _ask(label):
            try:
                return session.prompt(label)
            except Exception:
                return input(label)
        return _ask
    except Exception:
        return input


def chat(app,ask=None,out=console):
    if ask is None:
        ask = _default_ask()
    details = False
    out.print('Consultas independentes, sem histórico. /clear limpa o último resultado; /sources alterna fontes; /exit volta ao menu.')
    while True:
        try:
            question = ask('Você > ').strip()
            if not question:
                continue
            if question == '/exit':
                return
            if question == '/clear':
                if app._pipeline:
                    app.pipeline.clear_memory()
                out.print('Último resultado limpo.')
            elif question == '/sources':
                details = not details
                if app._pipeline:
                    app.pipeline.sync()
                    show_sources(app.pipeline.last_result,out)
                out.print('Detalhes de fontes: '+('ativados' if details else 'desativados'))
            else:
                respond(app,question,out,details)
        except EOFError:
            return
        except KeyboardInterrupt:
            out.print('\nResposta cancelada. /exit para sair.')
        except (ValueError,RuntimeError,OSError) as error:
            out.print(str(error),style='red',markup=False)
        except Exception as error:
            out.print(f'Erro no chat: {error}',style='red',markup=False)
