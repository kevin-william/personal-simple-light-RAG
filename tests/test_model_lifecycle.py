from types import SimpleNamespace
from src.models.lifecycle import ModelLifecycle


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
