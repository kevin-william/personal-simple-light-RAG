import subprocess
import sys
from src.config import ROOT


def test_cli_status_list_and_reset_requires_confirmation(tmp_path):
    def run(*args):
        return subprocess.run([sys.executable,str(ROOT/'main.py'),'--profile','cpu','--data-dir',str(tmp_path),*args],capture_output=True,text=True)
    assert run('--status').returncode == 0
    assert run('--list').returncode == 0
    assert run('--reset').returncode == 2
    assert run('--ask','q').returncode == 1
