from .models.llm import LLM
from .models.embeddings import Embedder
from .models.lifecycle import ModelLifecycle
from .metrics import Metrics
from .operations import OperationGate,exclusive


class Application:
    def __init__(self, settings):
        self.settings = settings
        self.operations = OperationGate()
        self.llm, self.embedder = LLM(settings), Embedder(settings)
        self.metrics = Metrics()
        self.llm.metrics = self.embedder.metrics = self.metrics
        self.lifecycle = ModelLifecycle(self.llm,self.embedder,settings.memory_mode)
        self._catalog = self._ingestor = self._lock = None
        self._pipeline = None

    @property
    @exclusive(read=True)
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
    @exclusive(read=True)
    def ingestor(self):
        if self._ingestor is None:
            from .rag.vectorstore import VectorStore
            from .rag.ingestion import Ingestor
            self._ingestor = Ingestor(self.settings,self.catalog,VectorStore(self.settings),self.embedder,operations=self.operations)
            self._ingestor.metrics = self.metrics
            for issue in self._ingestor.recover():
                import warnings
                warnings.warn(issue,stacklevel=2)
        return self._ingestor

    @exclusive
    def close(self):
        try:
            self.lifecycle.close()
        finally:
            try:
                if self._catalog:
                    self._catalog.close()
                    self._catalog = None
            finally:
                if self._lock:
                    self._lock.release()
                    self._lock = None

    @exclusive
    def reset(self,confirmed=False):
        if not confirmed:
            raise ValueError('Reset exige confirmação explícita.')
        from .rag.vectorstore import VectorStore
        # Reset must work even when the old collection fingerprint is incompatible.
        self.catalog.clear()
        store = VectorStore.reset_collection(self.settings)
        for version in self.catalog.all_versions():
            self.catalog.forget_version(version['id'])
        self._ingestor = None
        self._pipeline = None
        return {'reset':True, 'warnings':[]}

    @property
    @exclusive(read=True)
    def pipeline(self):
        if self._pipeline is None:
            from .rag.pipeline import Pipeline
            self._pipeline = Pipeline(self.settings,self.llm,self.embedder,self.ingestor,metrics=self.metrics,operations=self.operations)
        return self._pipeline
