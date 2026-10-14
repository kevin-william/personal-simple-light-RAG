from pathlib import Path
from hashlib import sha256
import json
import os


def digest(path):
    h = sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


class ModelCache:
    def __init__(self, settings, hub=None):
        self.settings = settings
        self.root = settings.models_dir
        self.hub = hub

    def directory(self, kind):
        return self.root / kind

    def spec(self, kind):
        s = self.settings
        return (s.model_repo_id, s.model_revision) if kind == 'llm' else (s.embedding_model_name, s.embedding_model_revision)

    def verify(self, kind, full=True):
        directory = self.directory(kind)
        manifest = directory / 'manifest.json'
        if not manifest.is_file():
            raise RuntimeError(f'Cache {kind} ausente/incompleto. Execute --prepare.')
        data = json.loads(manifest.read_text(encoding='utf-8'))
        repo, revision = self.spec(kind)
        if data['repo'] != repo or data['revision'] != revision:
            raise RuntimeError(f'Revisão do cache {kind} incompatível. Execute --prepare.')
        required = [self.settings.model_filename] if kind == 'llm' else ['model.safetensors', 'tokenizer.json', 'modules.json', 'config.json']
        if not all(name in data['files'] for name in required):
            raise RuntimeError(f'Manifesto {kind} incompleto.')
        for name, info in data['files'].items():
            path = (directory / name).resolve()
            if not path.is_relative_to(directory.resolve()) or not path.is_file():
                raise RuntimeError(f'Artefato {kind} ausente ou caminho inválido: {name}')
            if path.stat().st_size != info['size'] or (full and digest(path) != info['sha256']):
                raise RuntimeError(f'Artefato {kind} corrompido: {name}. Repita --prepare.')
        if kind == 'llm':
            with (directory / self.settings.model_filename).open('rb') as stream:
                if stream.read(4) != b'GGUF':
                    raise RuntimeError('Arquivo não é um GGUF válido.')
        return directory

    def prepare(self, kind, offline=False):
        try:
            return self.verify(kind)
        except (RuntimeError, ValueError, KeyError, OSError):
            if offline:
                raise RuntimeError(f'Cache {kind} inválido/ausente no modo offline. Execute --prepare com rede.')
        hub = self.hub
        if hub is None:
            import huggingface_hub as hub
        repo, revision = self.spec(kind)
        if len(revision) != 40:
            raise RuntimeError('Configure uma revisão imutável do Hub (SHA de 40 caracteres).')
        directory = self.directory(kind)
        directory.mkdir(parents=True, exist_ok=True)
        if kind == 'llm':
            hub.hf_hub_download(repo_id=repo, filename=self.settings.model_filename, revision=revision, local_dir=directory)
        else:
            hub.snapshot_download(repo_id=repo, revision=revision, local_dir=directory,
                                  allow_patterns=['*.json', '*.txt', '*.model', '*.safetensors', '1_Pooling/*.json'])
        remote = hub.HfApi().model_info(repo, revision=revision, files_metadata=True)
        siblings = {x.rfilename: x for x in remote.siblings}
        files = {}
        for path in directory.rglob('*'):
            if not path.is_file() or '.cache' in path.parts or path.name.startswith('manifest'):
                continue
            name = path.relative_to(directory).as_posix()
            if name not in siblings:
                continue
            metadata = siblings[name]
            actual = digest(path)
            lfs = getattr(metadata, 'lfs', None)
            expected = getattr(lfs, 'sha256', None) if lfs else None
            if (metadata.size is not None and metadata.size != path.stat().st_size) or (expected and expected != actual):
                # Hub's local_dir bookkeeping must not make a corrupt file appear cached.
                path.unlink()
                cache = directory / '.cache/huggingface/download' / (name + '.metadata')
                cache.unlink(missing_ok=True)
                raise RuntimeError(f'Download inválido: {name}; repita --prepare.')
            files[name] = {'size': path.stat().st_size, 'sha256': actual}
        manifest = {'repo': repo, 'revision': revision, 'files': files}
        temporary = directory / 'manifest.pending'
        temporary.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        os.replace(temporary, directory / 'manifest.json')
        return self.verify(kind)
