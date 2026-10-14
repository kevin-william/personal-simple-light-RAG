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
    args = parser.parse_args(argv)
    try:
        settings = load_settings(args.profile)
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
        print(json.dumps({'settings': settings.model_dump(mode='json'),
                          'hardware': 'Não verificado; nenhum modelo foi carregado.'}, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(2, f'Configuração inválida: {error}\n')
