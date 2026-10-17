from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def format_metrics(metrics):
    def duration(key):
        value = metrics.get(key)
        return f'{value:.2f}s' if value is not None else 'indisponível'
    native = metrics.get('llama_native',{}).get('decode_tokens_per_second')
    delivery = metrics.get('delivery_tokens_per_second_estimate')
    rate = f'{native:.1f} tokens/s' if native is not None and metrics.get('llm_calls') else 'indisponível'
    estimated = f'{delivery:.1f} tokens/s' if delivery is not None else 'indisponível'
    return (f'Tempo: {duration("total_seconds")} | Primeiro texto: {duration("ttft_seconds")} | '
            f'Resposta: {duration("generation_seconds")}\nDecode nativo: {rate} | Entrega estimada: {estimated}')


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
