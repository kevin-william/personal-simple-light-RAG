from .models.llm import LLM
from .models.embeddings import Embedder
from .models.lifecycle import ModelLifecycle


class Application:
    def __init__(self, settings):
        self.settings = settings
        self.llm, self.embedder = LLM(settings), Embedder(settings)
        self.lifecycle = ModelLifecycle(self.llm,self.embedder,settings.memory_mode)
        self._catalog = self._ingestor = self._lock = None

    @property
    def catalog(self):
        if self._catalog is None:
            from filelock import FileLock,Timeout
            from .rag.catalog import Catalog
            self.settings.catalog_path.parent.mkdir(parents=True,exist_ok=True)
            lock = FileLock(str(self.settings.catalog_path)+'.runtime.lock')
            try:
                lock.acquire(timeout=0)
            except Timeout as error:
                raise RuntimeError('Esta base já está aberta em outro processo. Feche a outra instância.') from error
            try:
                self._catalog = Catalog(self.settings.catalog_path)
            except Exception:
                lock.release()
                raise
            self._lock = lock
        return self._catalog

    @property
    def ingestor(self):
        if self._ingestor is None:
            from .rag.vectorstore import VectorStore
            from .rag.ingestion import Ingestor
            self._ingestor = Ingestor(self.settings,self.catalog,VectorStore(self.settings),self.embedder)
            for issue in self._ingestor.recover():
                import warnings
                warnings.warn(issue,stacklevel=2)
        return self._ingestor

    def close(self):
        self.lifecycle.close()
        if self._catalog:
            self._catalog.close()
            self._catalog = None
        if self._lock:
            self._lock.release()
            self._lock = None
