import subprocess
import sys
import pytest
from src.config import Settings, load_settings, ROOT


def test_defaults_and_cpu():
    assert Settings(_env_file=None).llm_backend == 'cuda'
    assert Settings(_env_file=None).embedding_device == 'cpu'
    assert Settings(_env_file=None).model_filename == 'Phi-4-mini-instruct.Q8_0.gguf'
    assert load_settings('cpu', _env_file=None).n_gpu_layers == 0


@pytest.mark.parametrize('kwargs', [dict(chunk_overlap_chars=800), dict(context_size=512),
                                    dict(llm_backend='cpu'), dict(n_gpu_layers=0), dict(top_k=0)])
def test_invalid(kwargs):
    with pytest.raises(ValueError):
        Settings(_env_file=None, **kwargs)


def test_status_is_lazy(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / 'main.py'), '--status'], cwd=tmp_path, capture_output=True, text=True,encoding='utf-8')
    assert result.returncode == 0
    assert str(ROOT).replace('\\', '\\\\') in result.stdout
    code = 'from src.cli import main; main(["--status"]); import sys; assert "torch" not in sys.modules'
    assert subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True).returncode == 0


def test_explicit_cuda_profile_preserves_partial_offload(monkeypatch):
    monkeypatch.setenv('LLM_BACKEND','cpu')
    monkeypatch.setenv('N_GPU_LAYERS','0')
    assert load_settings('cuda',_env_file=None).n_gpu_layers==-1
    monkeypatch.setenv('N_GPU_LAYERS','12')
    assert load_settings('cuda',_env_file=None).n_gpu_layers==12


def test_mixed_profile_overrides_devices_without_changing_index(monkeypatch):
    baseline = Settings(_env_file=None)
    monkeypatch.setenv('EMBEDDING_DEVICE','cuda')
    monkeypatch.setenv('MEMORY_MODE','alternating')
    monkeypatch.setenv('N_GPU_LAYERS','12')
    settings = load_settings('mixed',_env_file=None)
    assert (settings.llm_backend,settings.embedding_device,settings.memory_mode)==('cuda','cpu','resident')
    assert settings.n_gpu_layers == 12
    assert settings.fingerprint == baseline.fingerprint
    assert load_settings(None,_env_file=None).embedding_device == 'cuda'
    assert load_settings('cuda',_env_file=None).embedding_device == 'cuda'


def test_old_memory_limits_are_ignored(monkeypatch):
    monkeypatch.setenv('QUERY_RESOLUTION_MAX_TOKENS','999999')
    monkeypatch.setenv('MEMORY_SUMMARY_MAX_TOKENS','999999')
    assert Settings(_env_file=None).context_size == 4096


@pytest.mark.parametrize('saved,expected',[('cpu','cpu'),('cuda','cuda'),('mixed','cuda')])
def test_saved_profiles_keep_cpu_but_do_not_force_legacy_gpu_embeddings(tmp_path,monkeypatch,capsys,saved,expected):
    import json
    from src.cli import main
    (tmp_path/'rag-profile.txt').write_text(saved,encoding='utf-8')
    monkeypatch.setattr(sys,'prefix',str(tmp_path))
    assert main(['--status'])==0
    report=json.loads(capsys.readouterr().out)
    assert report['settings']['llm_backend']==expected
    assert report['settings']['embedding_device']=='cpu'
    assert report['conversation_memory'] is False
