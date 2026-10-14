import pytest
from tests.test_ingestion import service


def test_identity_delete_alias_and_reset(tmp_path):
    i = service(tmp_path)
    a,b = tmp_path/'a/doc.txt',tmp_path/'b/doc.txt'
    a.parent.mkdir()
    b.parent.mkdir()
    a.write_text('shared')
    b.write_text('shared')
    aid = i.ingest_file(a)['id']
    bid = i.ingest_file(b)['id']
    with pytest.raises(ValueError):
        i.delete_source(aid)
    assert len(i.catalog.list_sources()) == 2
    i.delete_source(aid,True)
    assert i.store.collection.count() == 1
    assert i.query([1.,0.],4)[0].metadata['source'] == str(b)
    assert not i.delete_source(aid,True)['removed']
    with pytest.raises(ValueError):
        i.reset()
    i.delete_source(bid,True)
    assert i.store.collection.count() == 0
    i.ingest_file(a)
    i.reset(True)
    assert not i.catalog.list_sources() and not i.catalog.active_versions()


def test_failed_cleanup_is_invisible_and_recoverable(tmp_path):
    i = service(tmp_path)
    a = tmp_path/'a.txt'
    a.write_text('old')
    aid = i.ingest_file(a)['id']
    original = i.store.delete_version
    def fail(version):
        raise OSError('locked')
    i.store.delete_version = fail
    assert i.delete_source(aid,True)['warnings']
    assert not i.query([1.,0.],4)
    i.store.delete_version = original
    i.recover()
    assert i.store.collection.count() == 0
