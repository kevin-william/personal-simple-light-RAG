import gc
import math
from ..rag.loaders import clean_text
from ..rag.splitter import split_documents
from .downloader import ModelCache
from .hardware import require_device
from ..metrics import measured


class Embedder:
    def __init__(self, settings, factory=None, dimension=1024):
        self.settings, self.factory, self.dimension = settings, factory, dimension
        self.model = None
        self.verified = False

    @measured('embeddings_load',lambda self:self.model is None)
    def load(self):
        if hasattr(self, 'before_load'):
            self.before_load()
        if self.model is not None:
            return self.model
        if self.factory:
            self.model = self.factory()
        else:
            require_device(self.settings, 'embeddings')
            cache = ModelCache(self.settings)
            directory = cache.verify('embeddings', full=not self.verified)
            self.verified = True
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(str(directory), device=self.settings.embedding_device, local_files_only=True)
            self.model.max_seq_length = self.settings.embedding_max_tokens
        return self.model

    def unload(self):
        self.model = None
        gc.collect()
        import sys
        if 'torch' in sys.modules and sys.modules['torch'].cuda.is_available():
            sys.modules['torch'].cuda.empty_cache()

    def length(self, text):
        return len(self.load().tokenizer.encode(clean_text(text), add_special_tokens=True))

    def prepare_chunks(self, chunks):
        result = []
        for chunk in chunks:
            if self.length(chunk.text) <= self.settings.embedding_max_tokens:
                result.append(chunk)
            else:
                size = len(chunk.text) // 2
                if size < 1:
                    raise ValueError('Trecho não cabe no tokenizer BGE-M3.')
                parts = split_documents([chunk], size, min(self.settings.chunk_overlap_chars, size // 4))
                base = chunk.metadata.get('offset', 0)
                for part in parts:
                    part.metadata['offset'] += base
                    part.metadata['end_offset'] += base
                result.extend(self.prepare_chunks(parts))
        for i, chunk in enumerate(result):
            chunk.metadata['position'] = i
        return result

    @measured('embeddings')
    def encode(self, texts):
        texts = [clean_text(t) for t in texts]
        if not texts:
            return []
        if any(not t or self.length(t) > self.settings.embedding_max_tokens for t in texts):
            raise ValueError('Entrada vazia ou longa demais para BGE-M3; reduza a pergunta ou redivida documentos.')
        try:
            vectors = self.load().encode(texts, batch_size=self.settings.embedding_batch_size,
                                         normalize_embeddings=True, show_progress_bar=False)
        except RuntimeError as error:
            if 'memory' in str(error).lower():
                raise RuntimeError('Memória insuficiente no BGE-M3. Reduza EMBEDDING_BATCH_SIZE ou use modo alternado/CPU.') from error
            raise
        vectors = vectors.tolist() if hasattr(vectors, 'tolist') else vectors
        for vector in vectors:
            if len(vector) != self.dimension or not all(math.isfinite(v) for v in vector):
                raise ValueError('Embedding com dimensão/valores inválidos.')
            norm = math.sqrt(sum(v*v for v in vector))
            if not math.isclose(norm, 1, abs_tol=1e-3):
                raise ValueError('Embedding não normalizado ou nulo.')
        if len(vectors) != len(texts):
            raise ValueError('Quantidade de embeddings inconsistente.')
        return vectors
