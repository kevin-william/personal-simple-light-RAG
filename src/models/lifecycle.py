class ModelLifecycle:
    def __init__(self, llm, embedder, mode='resident'):
        self.llm, self.embedder, self.mode = llm, embedder, mode
        self.llm.before_load = lambda: self.select('llm')
        self.embedder.before_load = lambda: self.select('embeddings')

    def select(self, component):
        if self.mode == 'alternating':
            other = self.embedder if component == 'llm' else self.llm
            if getattr(other, 'model', True) is not None:
                other.unload()

    def close(self):
        self.llm.unload()
        self.embedder.unload()
