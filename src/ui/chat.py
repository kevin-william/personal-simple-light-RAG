from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text
from .console import console,show_sources


def respond(app,question,out=console,details=False):
    if not app.catalog.list_sources():
        out.print('Base vazia. Adicione documentos pelo menu ou --add.')
        return None
    stream = app.pipeline.stream(question)
    text = ''
    try:
        with Live(Text('Resolvendo pergunta e buscando evidências…'),console=out,refresh_per_second=8) as live:
            for token in stream:
                text += token
                live.update(Markdown(text))
    finally:
        stream.close()
    answer = app.pipeline.last_result
    for warning in answer.warnings:
        out.print(warning,style='yellow',markup=False)
    if details:
        show_sources(answer,out)
    else:
        out.print(f'{len(answer.cited)} fontes citadas. /sources exibe detalhes.',style='dim')
    return answer


def chat(app,ask=None,out=console):
    if ask is None:
        from prompt_toolkit import PromptSession
        session = PromptSession()
        ask = lambda label: session.prompt(label)
    details = False
    out.print('Chat: /clear limpa memória; /sources alterna fontes; /exit volta ao menu.')
    while True:
        try:
            question = ask('Você > ').strip()
            if not question:
                continue
            if question == '/exit':
                return
            if question == '/clear':
                if app._pipeline:
                    app.pipeline.memory.clear()
                out.print('Memória limpa.')
            elif question == '/sources':
                details = not details
                if app._pipeline:
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
