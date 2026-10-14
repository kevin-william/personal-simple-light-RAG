import argparse
import json
from .config import load_settings


def main(argv=None):
    parser = argparse.ArgumentParser(description='Chat local com seus documentos')
    parser.add_argument('--profile', choices=['cuda', 'cpu'])
    parser.add_argument('--status', action='store_true')
    args = parser.parse_args(argv)
    try:
        settings = load_settings(args.profile)
        print(json.dumps({'settings': settings.model_dump(mode='json'),
                          'hardware': 'Não verificado; nenhum modelo foi carregado.'}, ensure_ascii=False, indent=2))
        return 0
    except ValueError as error:
        parser.exit(2, f'Configuração inválida: {error}\n')
