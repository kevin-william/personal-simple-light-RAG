from .console import console,show_documents
from .ingestion import ingest,remove,reset


def menu(app,ask=input,out=console):
    while True:
        out.print('\n[bold]Personal Simple Light RAG[/bold]\n'
                  '1. Chat com documentos\n2. Adicionar/atualizar arquivo ou pasta\n3. Listar documentos\n'
                  '4. Remover origem\n5. Resetar base\n6. Configuração/hardware\n0. Sair')
        try:
            choice = ask('Opção: ').strip()
            if choice == '0':
                return
            if choice == '1':
                from .chat import chat
                chat(app,out=out)
            elif choice == '2':
                ingest(app,ask('Arquivo/pasta: ').strip().strip('"'),out)
            elif choice == '3':
                show_documents(app.catalog.list_sources(),out)
            elif choice == '4':
                show_documents(app.catalog.list_sources(),out)
                remove(app,ask('ID de origem: ').strip(),ask,out)
            elif choice == '5':
                reset(app,ask,out)
            elif choice == '6':
                from ..models.hardware import diagnostic
                out.print(app.settings.model_dump(mode='json'))
                out.print(diagnostic())
                out.print({'llm_offload_observed':app.llm.offload_effective})
            else:
                out.print('Opção inválida.')
        except (EOFError,KeyboardInterrupt):
            out.print('\nVoltando/sair. Use 0 para sair.')
            if isinstance(__import__('sys').exc_info()[1],EOFError):
                return
        except (ValueError,RuntimeError,OSError) as error:
            out.print(str(error),style='red',markup=False)
