from types import SimpleNamespace
from pathlib import Path
from src.models.hardware import diagnostic


def test_independent_backend_detection():
    torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: True, get_device_name=lambda i: 'GPU'),
                            version=SimpleNamespace(cuda='12.4'), __version__='test')
    llama = SimpleNamespace(llama_supports_gpu_offload=lambda: False, __version__='test')
    report = diagnostic(lambda name: {'torch': torch, 'llama_cpp': llama}[name])
    assert report['torch_cuda'] and not report['cuda_ready']
    assert report['offload_effective'] is None


def test_script_uses_binary_profiles():
    text = Path('scripts/setup.ps1').read_text()
    assert "[string]$Profile = 'mixed'" in text
    assert 'https://download.pytorch.org/whl/cpu' in text
    assert 'https://download.pytorch.org/whl/cu124' in text
    assert '--only-binary=:all:' in text
    assert 'if ($LASTEXITCODE -ne 0)' in text


def test_mixed_diagnostic_only_needs_llm_cuda():
    from src.config import load_settings
    torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:False),
                            version=SimpleNamespace(cuda=None),__version__='test')
    llama = SimpleNamespace(llama_supports_gpu_offload=lambda:True,__version__='test')
    report=diagnostic(lambda name:{'torch':torch,'llama_cpp':llama}[name],settings=load_settings('mixed',_env_file=None))
    assert report['profile_ready'] and not report['cuda_ready']
