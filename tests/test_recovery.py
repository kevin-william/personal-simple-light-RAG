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


def test_actual_process_exit_before_activation(tmp_path):
    import subprocess,sys
    from src.config import ROOT
    setup = "from pathlib import Path; from tests.test_ingestion import service; import sys; root=Path(sys.argv[1]); p=root/'active.txt'; p.write_text('active'); i=service(root); i.ingest_file(p); i.catalog.close()"
    crash = "from pathlib import Path; from tests.test_ingestion import service; from src.rag.loaders import Document; import sys,os; i=service(Path(sys.argv[1])); i.catalog.stage('crashed','hash','fp',1); i.store.add('crashed',[Document('partial',{})],[[1.,0.]]); os._exit(23)"
    assert subprocess.run([sys.executable,'-c',setup,str(tmp_path)],cwd=ROOT,capture_output=True).returncode==0
    assert subprocess.run([sys.executable,'-c',crash,str(tmp_path)],cwd=ROOT,capture_output=True).returncode==23
    i = service(tmp_path)
    assert i.catalog.version('crashed')['state']=='pending'
    i.recover()
    assert not i.catalog.version('crashed')
    assert i.query([1.,0.],4)[0].text=='active'
