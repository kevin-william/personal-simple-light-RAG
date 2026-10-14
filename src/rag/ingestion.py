from pathlib import Path
from hashlib import sha256
import warnings
from .loaders import discover, load_file
from .splitter import split_documents
from ..models.downloader import digest
from ..metrics import measured


class Ingestor:
    def __init__(self, settings, catalog, store, embedder):
        self.settings, self.catalog, self.store, self.embedder = settings, catalog, store, embedder

    def recover(self):
        active = self.catalog.active_versions()
        issues = []
        for version in self.catalog.all_versions():
            if version['id'] in active:
                if self.store.count_version(version['id']) != version['expected']:
                    raise RuntimeError('Índice ativo incompleto/corrompido. Preserve a base e reimporte em uma nova coleção.')
            else:
                try:
                    self.store.delete_version(version['id'])
                    self.catalog.forget_version(version['id'])
                except Exception as error:
                    issues.append(f'Limpeza pendente {version["id"]}: {error}')
        for version in self.store.versions() - active:
            try:
                self.store.delete_version(version)
            except Exception as error:
                issues.append(f'Vetores órfãos: {error}')
        return issues

    @measured('indexing')
    def ingest_file(self, path):
        path = Path(path).resolve()
        if path.suffix.lower() not in {'.pdf','.md','.txt'}:
            raise ValueError('Formato não suportado. Use PDF, TXT ou Markdown.')
        content_hash = digest(path)
        kind = 'pdf' if path.suffix.lower() == '.pdf' else 'text'
        version = sha256((content_hash+self.settings.fingerprint+kind).encode()).hexdigest()
        existing = self.catalog.source(path)
        if existing and existing['version'] == version:
            return {'path':str(path), 'status':'skipped', 'id':existing['id']}
        known = self.catalog.version(version)
        if known and known['state'] == 'active' and self.store.count_version(version) != known['expected']:
            if version in self.catalog.active_versions():
                raise RuntimeError('Versão ativa inconsistente; preserve a base e reimporte em nova coleção.')
            self.store.delete_version(version)
            self.catalog.forget_version(version)
            known = None
        if known and known['state'] == 'active':
            identifier = self.catalog.activate(version,path)
            issues = self.recover()
            return {'path':str(path),'status':'updated' if existing else 'added','id':identifier,'alias':True,'warnings':issues}
        chunks = self.embedder.prepare_chunks(split_documents(load_file(path),
                self.settings.chunk_size_chars,self.settings.chunk_overlap_chars))
        if not chunks:
            raise ValueError('Documento sem trechos indexáveis.')
        self.catalog.stage(version,content_hash,self.settings.fingerprint,len(chunks))
        try:
            self.store.delete_version(version)
            vectors = self.embedder.encode([c.text for c in chunks])
            self.store.add(version,chunks,vectors)
            if self.store.count_version(version) != len(chunks):
                raise RuntimeError('Versão vetorial incompleta; não ativada.')
            if digest(path) != content_hash:
                raise RuntimeError('Arquivo mudou durante a indexação; repita a importação.')
            identifier = self.catalog.activate(version,path)
        except Exception as error:
            if version not in self.catalog.active_versions():
                self.catalog.fail(version,error)
                try:
                    self.store.delete_version(version)
                except Exception:
                    pass  # Failed version remains invisible; recover retries cleanup.
            raise
        issues = self.recover()
        return {'path':str(path),'status':'updated' if existing else 'added','id':identifier,'chunks':len(chunks),'warnings':issues}

    def ingest_path(self, path, progress=None):
        paths = discover(path)
        results = []
        for i, item in enumerate(paths,1):
            try:
                with warnings.catch_warnings(record=True) as caught:
                    result = self.ingest_file(item)
                result.setdefault('warnings',[]).extend(str(w.message) for w in caught)
            except Exception as error:
                result = {'path':str(item),'status':'failed','error':str(error)}
            results.append(result)
            if progress:
                progress(i,len(paths),result)
        return results

    def query(self, vector, k):
        hits = self.store.query(vector,k,self.catalog.active_versions())
        sources = self.catalog.list_sources()
        for hit in hits:
            aliases = [s for s in sources if s['version'] == hit.metadata['version']]
            if aliases:
                hit.metadata = dict(hit.metadata, source=aliases[0]['path'], document_id=aliases[0]['id'])
                hit.metadata['aliases'] = [s['path'] for s in aliases]
        return hits

    def reference_hits(self,references):
        from .vectorstore import Hit
        active = self.catalog.active_versions()
        live_sources = {s['id']:s for s in self.catalog.list_sources()}
        result = []
        for reference in references:
            if reference.get('version') not in active:
                continue
            live = live_sources.get(reference.get('document_id'))
            if not live or live['version'] != reference['version']:
                continue
            record = self.store.collection.get(ids=[reference['id']],include=['documents','metadatas'])
            if record['ids']:
                meta = dict(record['metadatas'][0],source=reference['source'],citation=reference['citation'])
                result.append(Hit(reference['id'],record['documents'][0],meta,reference.get('distance',0.)))
        return result

    def delete_source(self, identifier, confirmed=False):
        if not confirmed:
            raise ValueError('Exclusão exige confirmação explícita.')
        removed = self.catalog.remove_source(identifier)
        return {'removed':removed, 'warnings':self.recover()}

    def reset(self, confirmed=False):
        if not confirmed:
            raise ValueError('Reset exige confirmação explícita.')
        self.catalog.clear()
        return {'warnings':self.recover()}
