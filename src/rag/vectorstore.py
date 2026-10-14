from dataclasses import dataclass


@dataclass
class Hit:
    id: str
    text: str
    metadata: dict
    distance: float

    @property
    def similarity(self):
        return 1 - self.distance


class VectorStore:
    def __init__(self, settings):
        import chromadb
        from chromadb.config import Settings
        self.client = chromadb.PersistentClient(path=str(settings.chroma_persist_dir),
                                               settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(settings.collection_name,
            embedding_function=None, metadata={'hnsw:space':'cosine', 'fingerprint': settings.fingerprint})
        meta = self.collection.metadata or {}
        if meta.get('fingerprint') != settings.fingerprint or meta.get('hnsw:space') != 'cosine':
            raise ValueError('Índice incompatível com configuração de embeddings/cosseno. Crie nova base ou faça reset.')

    def add(self, version, chunks, vectors):
        if len(chunks) != len(vectors):
            raise ValueError('Quantidade de chunks/embeddings inconsistente.')
        batch = 256
        for start in range(0,len(chunks),batch):
            subset = chunks[start:start+batch]
            ids = [f'{version}:{start+i}' for i in range(len(subset))]
            self.collection.upsert(ids=ids, documents=[c.text for c in subset],
                embeddings=vectors[start:start+batch],
                metadatas=[dict(c.metadata, version=version) for c in subset])

    def count_version(self, version):
        return len(self.collection.get(where={'version':version}, include=[])['ids'])

    def delete_version(self, version):
        self.collection.delete(where={'version':version})

    def versions(self):
        records = self.collection.get(include=['metadatas'])
        return {m['version'] for m in records['metadatas']}

    def query(self, vector, k, active_versions=None):
        if active_versions is not None and not active_versions:
            return []
        count = self.collection.count()
        if not count:
            return []
        # Overfetch until k active results or exhaustion, not a fixed multiplier.
        limit = min(max(k,1), count)
        while True:
            data = self.collection.query(query_embeddings=[vector], n_results=limit,
                                         include=['documents','metadatas','distances'])
            hits = [Hit(i,t,m,float(d)) for i,t,m,d in zip(data['ids'][0], data['documents'][0],
                   data['metadatas'][0], data['distances'][0])
                   if active_versions is None or m['version'] in active_versions]
            if len(hits) >= k or limit == count:
                return hits[:k]
            limit = min(count,limit*2)
