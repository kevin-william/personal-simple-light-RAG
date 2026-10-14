from rich.progress import Progress
from .console import console,show_documents


def ingest(app,path,out=console):
    with Progress(console=out) as progress:
        task = progress.add_task('Lendo, dividindo e indexando',total=None)
        def update(done,total,result):
            progress.update(task,total=total,completed=done,description=result['status'])
        results = app.ingestor.ingest_path(path,update)
    for item in results:
        out.print(f'{item["status"]}: {item["path"]}',markup=False)
        if item.get('error'):
            out.print(item['error'],style='red',markup=False)
        for message in item.get('warnings',[]):
            out.print(message,style='yellow',markup=False)
    out.print({status:sum(r['status']==status for r in results) for status in ('added','updated','skipped','failed')})
    return results


def remove(app,identifier,ask=input,out=console):
    if ask('Confirma remover esta origem da base? Digite SIM: ').strip() != 'SIM':
        out.print('Cancelado.')
        return False
    result = app.ingestor.delete_source(identifier,confirmed=True)
    out.print(result)
    return result['removed']


def reset(app,ask=input,out=console):
    if ask('Confirma limpar toda a base? Digite RESET: ').strip() != 'RESET':
        out.print('Cancelado.')
        return False
    out.print(app.ingestor.reset(confirmed=True))
    return True
