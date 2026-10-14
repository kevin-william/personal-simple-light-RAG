import importlib


def diagnostic(importer=importlib.import_module):
    result = {'torch_cuda': False, 'llama_gpu_support': False, 'offload_effective': None}
    for module in ('torch', 'llama_cpp'):
        try:
            obj = importer(module)
            if module == 'torch':
                result['torch_cuda'] = bool(obj.cuda.is_available())
                result['torch_version'] = obj.__version__
                result['torch_cuda_version'] = obj.version.cuda
                result['gpu'] = obj.cuda.get_device_name(0) if result['torch_cuda'] else None
            else:
                result['llama_gpu_support'] = bool(obj.llama_supports_gpu_offload())
                result['llama_version'] = obj.__version__
        except (ImportError, OSError, RuntimeError) as error:
            result[module + '_error'] = str(error)
    result['cuda_ready'] = result['torch_cuda'] and result['llama_gpu_support']
    result['note'] = 'Offload efetivo só é verificado durante carregamento. Use --profile cpu se CUDA não estiver disponível.'
    return result


def require_device(settings, component):
    if getattr(settings, 'embedding_device' if component == 'embeddings' else 'llm_backend') == 'cpu':
        return
    report = diagnostic()
    supported = report['torch_cuda'] if component == 'embeddings' else report['llama_gpu_support']
    if not supported:
        raise RuntimeError(f'CUDA indisponível para {component}. Execute setup.ps1 ou escolha --profile cpu. {report}')
