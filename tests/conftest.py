import pytest


def pytest_addoption(parser):
    parser.addoption('--models', action='store_true', help='Executar testes com modelos reais em cache')
    parser.addoption('--model-profile', choices=['mixed', 'cpu', 'cuda'], default='cpu')


@pytest.fixture
def anyio_backend():
    return 'asyncio'


def pytest_collection_modifyitems(config, items):
    if not config.getoption('--models'):
        for item in items:
            if 'integration_models' in item.keywords:
                item.add_marker(pytest.mark.skip(reason='Use --models após preparar o cache.'))
