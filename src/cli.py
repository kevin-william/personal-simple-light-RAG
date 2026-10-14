import argparse
import json
from .config import load_settings


def main(argv=None):
    parser = argparse.ArgumentParser(description='Chat local com seus documentos')
    parser.add_argument('--profile', choices=['cuda', 'cpu'])
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--diagnose', action='store_true')
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--add', metavar='ARQUIVO_OU_PASTA')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--delete', metavar='ID_ORIGEM')
    parser.add_argument('--reset', action='store_true')
    parser.add_argument('--yes', action='store_true', help='Confirma exclusão/reset não interativo')
    parser.add_argument('--data-dir', help='Diretório isolado para a base')
    args = parser.parse_args(argv)
    try:
        from pathlib import Path
        overrides = {'chroma_persist_dir':Path(args.data_dir)/'chroma'} if args.data_dir else {}
        settings = load_settings(args.profile,**overrides)
        if args.prepare:
            from .models.downloader import ModelCache
            cache = ModelCache(settings)
            for kind in ('llm', 'embeddings'):
                print(f'Preparando {kind}: {cache.prepare(kind, args.offline)}')
            return 0
        if args.diagnose:
            from .models.hardware import diagnostic
            report = diagnostic()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if settings.llm_backend == 'cpu' or report['cuda_ready'] else 1
        if args.status:
            print(json.dumps({'settings': settings.model_dump(mode='json'),
                             'hardware': 'Não verificado; nenhum modelo foi carregado.'}, ensure_ascii=False, indent=2))
            return 0
        from .application import Application
        from .ui.console import show_documents
        app = Application(settings)
        try:
            if args.add:
                from .ui.ingestion import ingest
                return 1 if any(r['status']=='failed' for r in ingest(app,args.add)) else 0
            if args.list:
                show_documents(app.catalog.list_sources())
            elif args.delete:
                print(app.ingestor.delete_source(args.delete,confirmed=args.yes))
            elif args.reset:
                print(app.ingestor.reset(confirmed=args.yes))
            else:
                from .ui.menu import menu
                menu(app)
        finally:
            app.close()
        return 0
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(2, f'Configuração inválida: {error}\n')
