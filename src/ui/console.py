from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def show_documents(sources,out=console):
    table = Table(title='Documentos indexados')
    table.add_column('ID de origem')
    table.add_column('Arquivo')
    table.add_column('Trechos',justify='right')
    for source in sources:
        table.add_row(source['id'],source['path'],str(source['chunks']))
    out.print(table)


def show_sources(answer,out=console):
    out.print(f'{len(answer.candidates)} candidatos recuperados; {len(answer.supplied)} fornecidos; {len(answer.cited)} citados.')
    cited = {h.id for h in answer.cited}
    inherited = answer.mode == 'transformation'
    if inherited:
        out.print('Fontes herdadas da resposta reformulada; similaridade da busca anterior.')
    for i,hit in enumerate(answer.cited if inherited else answer.supplied,1):
        i = hit.metadata.get('citation',i) if inherited else i
        label = 'citada' if hit.id in cited else 'fornecida, não citada'
        metadata = hit.metadata
        location = f'página {metadata["page"]}' if 'page' in metadata else f'linhas {metadata.get("line_start","?")}–{metadata.get("line_end","?")}'
        out.print(Panel(hit.text,title=f'[{i}] {metadata.get("source","")} ({location}) — {label}',
                        subtitle=f'Similaridade cosseno: {hit.similarity:.4f}',highlight=False))
