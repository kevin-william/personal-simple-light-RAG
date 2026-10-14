import pytest
from src.config import Settings
from src.rag.loaders import Document
from src.rag.vectorstore import VectorStore


def test_cosine_active_filter_persistence(tmp_path):
    s = Settings(root=tmp_path, _env_file=None)
    store = VectorStore(s)
    store.add('inactive', [Document('stale',{})], [[1.,0.]])
    store.add('active', [Document('right',{}),Document('orthogonal',{})], [[1.,0.],[0.,1.]])
    hits = store.query([1.,0.],2,{'active'})
    assert [h.text for h in hits] == ['right','orthogonal']
    assert hits[0].similarity == pytest.approx(1)
    assert hits[1].distance == pytest.approx(1)
    assert VectorStore(s).count_version('active') == 2
    store.delete_version('active')
    assert not store.query([1.,0.],4,{'active'})
    with pytest.raises(ValueError, match='incompatível'):
        VectorStore(Settings(root=tmp_path, chunk_size_chars=900, _env_file=None))
