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
