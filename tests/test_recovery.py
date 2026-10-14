from tests.test_ingestion import service
from src.rag.loaders import Document


def test_crash_pending_and_repeated_cleanup(tmp_path):
    i = service(tmp_path)
    path = tmp_path/'a.txt'
    path.write_text('active')
    i.ingest_file(path)
    i.catalog.stage('interrupted','hash','fp',1)
    i.store.add('interrupted',[Document('invisible',{})],[[1.,0.]])
    assert [h.text for h in i.query([1.,0.],4)] == ['active']
    i.recover()
    i.recover()
    assert not i.catalog.version('interrupted')
    assert i.store.count_version('interrupted') == 0
    assert i.query([1.,0.],4)[0].text == 'active'
