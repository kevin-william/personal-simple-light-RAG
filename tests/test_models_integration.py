"""Actual pinned models only; skips are not evidence that a gate passed."""
import pytest
from src.config import load_settings
from src.models.downloader import ModelCache
from src.models.llm import LLM
from src.models.embeddings import Embedder
from src.models.lifecycle import ModelLifecycle


@pytest.mark.integration_models
def test_real_embeddings_and_phi_offline(request):
    s = load_settings(request.config.getoption('--model-profile'),memory_mode='alternating')
    ModelCache(s).prepare('llm',offline=True)
    ModelCache(s).prepare('embeddings',offline=True)
    llm,embedder = LLM(s),Embedder(s)
    cycle = ModelLifecycle(llm,embedder,s.memory_mode)
    try:
        vectors = embedder.encode(['Como configurar autenticação OAuth2?','Como configurar autenticação OAuth2?'])
        assert len(vectors[0]) == 1024
        assert vectors[0] == pytest.approx(vectors[1],abs=1e-5)
        assert str(embedder.load().device).split(':')[0] == s.embedding_device
        result = ''.join(llm.stream([{'role':'user','content':'Responda apenas com a palavra OK.'}],max_tokens=16))
        assert 'OK' in result.upper()
        assert '<|end|>' not in result and '<|assistant|>' not in result
        assert (embedder.model is None) == (s.memory_mode=='alternating')
        if s.llm_backend == 'cuda':
            assert llm.offload_effective and llm.offload_effective['layers'] > 0
        else:
            assert llm.offload_effective['layers']==0
    finally:
        cycle.close()
