import pytest
from src.config import Settings
from src.rag.catalog import Catalog
from src.rag.vectorstore import VectorStore
from src.rag.ingestion import Ingestor


class FakeEmbedder:
    def prepare_chunks(self,chunks):
        return chunks
    def encode(self,texts):
        return [[1.,0.] for _ in texts]


def service(tmp_path):
    s = Settings(root=tmp_path, _env_file=None)
    catalog = Catalog(s.catalog_path)
    return Ingestor(s,catalog,VectorStore(s),FakeEmbedder())


def test_import_alias_and_noop(tmp_path):
    ingest = service(tmp_path)
    a,b = tmp_path/'a.txt',tmp_path/'b.txt'
    a.write_text('OAuth2 settings')
    b.write_text('OAuth2 settings')
    assert ingest.ingest_file(a)['status'] == 'added'
    assert ingest.ingest_file(a)['status'] == 'skipped'
    assert ingest.ingest_file(b)['alias']
    assert ingest.store.collection.count() == 1
    assert len(ingest.catalog.list_sources()) == 2
    assert ingest.query([1.,0.],4)[0].metadata['source'] == str(a)


def test_failed_import_invisible(tmp_path):
    ingest = service(tmp_path)
    path = tmp_path/'doc.txt'
    path.write_text('content')
    def fail(texts):
        raise RuntimeError('encode failed')
    ingest.embedder.encode = fail
    with pytest.raises(RuntimeError):
        ingest.ingest_file(path)
    assert not ingest.catalog.active_versions()
    ingest.recover()
    ingest.recover()
    assert not ingest.catalog.all_versions()
