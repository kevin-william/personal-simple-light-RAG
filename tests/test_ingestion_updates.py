import pytest
from tests.test_ingestion import service


def test_update_preserves_alias(tmp_path):
    i = service(tmp_path)
    a,b = tmp_path/'a.txt',tmp_path/'b.txt'
    a.write_text('old')
    b.write_text('old')
    i.ingest_file(a)
    i.ingest_file(b)
    a.write_text('new')
    assert i.ingest_file(a)['status'] == 'updated'
    assert i.store.collection.count() == 2
    assert {h.text for h in i.query([1.,0.],4)} == {'old','new'}
    b.write_text('new')
    i.ingest_file(b)
    assert i.store.collection.count() == 1


def test_failure_keeps_previous_and_directory_continues(tmp_path):
    i = service(tmp_path)
    a = tmp_path/'a.txt'
    a.write_text('old')
    i.ingest_file(a)
    a.write_text('new')
    original = i.store.add
    def fail(*args):
        original(*args)
        raise RuntimeError('partial write')
    i.store.add = fail
    with pytest.raises(RuntimeError):
        i.ingest_file(a)
    assert [h.text for h in i.query([1.,0.],4)] == ['old']
    i.store.add = original
    (tmp_path/'invalid.txt').write_bytes(b'\xff')
    results = i.ingest_path(tmp_path)
    assert {r['status'] for r in results} >= {'updated','failed'}
