from types import SimpleNamespace
import pytest
from src.config import Settings
from src.models.embeddings import Embedder
from src.rag.loaders import Document


class Encoder:
    tokenizer = SimpleNamespace(encode=lambda text, **kwargs: list(text))
    def encode(self, texts, **kwargs):
        self.texts, self.kwargs = texts, kwargs
        return [[1.,0.] for _ in texts]


def test_same_preprocessing_and_chunk_limits(tmp_path):
    fake = Encoder()
    embed = Embedder(Settings(root=tmp_path, embedding_max_tokens=16, _env_file=None), lambda:fake, 2)
    assert embed.encode(['e\u0301\r\n']) == [[1.,0.]]
    assert fake.texts == ['é'] and fake.kwargs['normalize_embeddings']
    with pytest.raises(ValueError, match='longa'):
        embed.encode(['A'*30])
    chunks = embed.prepare_chunks([Document('A'*50, {'offset':0,'line_start':1})])
    assert all(len(c.text)<=16 for c in chunks)
    assert len(chunks) > 1


def test_reject_bad_vectors(tmp_path):
    fake = Encoder()
    fake.encode = lambda texts, **kwargs: [[0.,0.]]
    embed = Embedder(Settings(root=tmp_path, _env_file=None), lambda:fake, 2)
    with pytest.raises(ValueError, match='normalizado'):
        embed.encode(['query'])


def test_auto_detect_embedding_dimension(tmp_path):
    fake = Encoder()
    fake.get_sentence_embedding_dimension = lambda: 384
    embed = Embedder(Settings(root=tmp_path, _env_file=None, embedding_dimension=1024), lambda:fake)
    assert embed.dimension == 1024
