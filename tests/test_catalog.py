import pytest
from src.rag.catalog import Catalog


def test_identity_aliases_activation(tmp_path):
    c = Catalog(tmp_path/'catalog.db')
    c.stage('v1','hash','fp',2)
    a,b = tmp_path/'a/doc.txt',tmp_path/'b/doc.txt'
    aid,bid = c.activate('v1',a),c.activate('v1',b)
    assert aid != bid and len(c.active_versions()) == 1
    assert c.generation == 2
    with pytest.raises(ValueError):
        c.stage('v1','hash','fp',2)
    assert c.remove_source(aid) and c.active_versions() == {'v1'}
    assert not c.remove_source(aid)
    assert len(Catalog(tmp_path/'catalog.db').list_sources()) == 1
    with pytest.raises(ValueError):
        c.activate('missing',a)
