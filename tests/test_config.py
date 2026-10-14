import subprocess
import sys
import pytest
from src.config import Settings, load_settings, ROOT


def test_defaults_and_cpu():
    assert Settings(_env_file=None).llm_backend == 'cuda'
    assert Settings(_env_file=None).model_filename == 'Phi-4-mini-instruct.Q8_0.gguf'
    assert load_settings('cpu', _env_file=None).n_gpu_layers == 0


@pytest.mark.parametrize('kwargs', [dict(chunk_overlap_chars=800), dict(context_size=512),
                                    dict(llm_backend='cpu'), dict(n_gpu_layers=0), dict(top_k=0)])
def test_invalid(kwargs):
    with pytest.raises(ValueError):
        Settings(_env_file=None, **kwargs)


def test_status_is_lazy(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / 'main.py'), '--status'], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0
    assert str(ROOT).replace('\\', '\\\\') in result.stdout
    code = 'from src.cli import main; main(["--status"]); import sys; assert "torch" not in sys.modules'
    assert subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True).returncode == 0
