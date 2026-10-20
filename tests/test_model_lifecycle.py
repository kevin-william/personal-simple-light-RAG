from types import SimpleNamespace
from src.models.lifecycle import ModelLifecycle
from src.config import Settings
from src.metrics import Metrics
import pytest


def test_alternating_and_close():
    calls = []
    llm = SimpleNamespace(unload=lambda:calls.append('llm'))
    embed = SimpleNamespace(unload=lambda:calls.append('embeddings'))
    cycle = ModelLifecycle(llm,embed,'alternating')
    llm.before_load()
    embed.before_load()
    assert calls == ['embeddings','llm']
    cycle.close()
    assert calls[-2:] == ['llm','embeddings']


class Component:
    def __init__(self, settings):
        self.settings=settings
        self.model=None
        self.factory=None
        self.metrics=Metrics()
        self.loads=self.unloads=0

    def load(self):
        self.before_load()
        if self.model is None:
            self.loads+=1
            self.model=object()
        return self.model

    def unload(self):
        self.unloads+=1
        self.model=None


@pytest.mark.parametrize('order',[('llm','embeddings'),('embeddings','llm')])
def test_mixed_keeps_both_models_for_five_queries(tmp_path,order):
    settings=Settings(root=tmp_path,_env_file=None)
    llm,embed=Component(settings),Component(settings)
    cycle=ModelLifecycle(llm,embed)
    components={'llm':llm,'embeddings':embed}
    for _ in range(5):
        for name in order:
            components[name].load()
    assert llm.loads==embed.loads==1
    assert llm.unloads==embed.unloads==0
    assert {e['device'] for e in cycle.events}=={'cpu','cuda'}
    cycle.close()
    assert llm.unloads==embed.unloads==1
    assert list(cycle.events)[-1]['reason']=='shutdown'


def test_shared_memory_still_evicts_when_requested(tmp_path,monkeypatch):
    import sys
    settings=Settings(root=tmp_path,llm_backend='cpu',n_gpu_layers=0,_env_file=None)
    directory=settings.models_dir/'embeddings'
    directory.mkdir(parents=True)
    (directory/'pytorch_model.bin').write_bytes(b'weights')
    monkeypatch.setitem(sys.modules,'psutil',SimpleNamespace(virtual_memory=lambda:SimpleNamespace(available=0)))
    llm,embed=Component(settings),Component(settings)
    cycle=ModelLifecycle(llm,embed)
    llm.load()
    embed.load()
    assert llm.model is None and embed.model is not None
    assert any(e['reason']=='memory_pressure' for e in cycle.events)
