import json
from src.config import Settings
from src.models.downloader import ModelCache, digest
import pytest


def test_integrity_and_offline_no_network(tmp_path):
    s = Settings(root=tmp_path, _env_file=None)
    c = ModelCache(s, hub=object())
    with pytest.raises(RuntimeError, match='offline'):
        c.prepare('llm', offline=True)
    directory = c.directory('llm')
    directory.mkdir(parents=True)
    path = directory / s.model_filename
    path.write_bytes(b'GGUFgood')
    manifest = {'repo': s.model_repo_id, 'revision': s.model_revision,
                'files': {s.model_filename: {'size': 8, 'sha256': digest(path)}}}
    (directory / 'manifest.json').write_text(json.dumps(manifest))
    assert c.prepare('llm', offline=True) == directory
    path.write_bytes(b'GGUFbad!')
    with pytest.raises(RuntimeError, match='corrompido'):
        c.verify('llm')
    manifest['revision'] = 'other'
    (directory / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(RuntimeError, match='incompatível'):
        c.verify('llm')


def test_official_bge_bin_weights_are_supported(tmp_path):
    s = Settings(root=tmp_path,_env_file=None)
    c = ModelCache(s)
    directory = c.directory('embeddings')
    directory.mkdir(parents=True)
    files = {}
    for name in ('pytorch_model.bin','tokenizer.json','modules.json','config.json'):
        path = directory/name
        path.write_bytes(b'fixture')
        files[name] = {'size':7,'sha256':digest(path)}
    (directory/'manifest.json').write_text(json.dumps({'repo':s.embedding_model_name,'revision':s.embedding_model_revision,'files':files}))
    assert c.prepare('embeddings',offline=True)==directory


@pytest.mark.parametrize('content',['[]','{}','{"repo":"x","revision":"x","files":[]}'])
def test_malformed_manifest_is_actionable(tmp_path,content):
    c = ModelCache(Settings(root=tmp_path,_env_file=None))
    c.directory('llm').mkdir(parents=True)
    (c.directory('llm')/'manifest.json').write_text(content)
    with pytest.raises(RuntimeError,match='inválido'):
        c.verify('llm')
