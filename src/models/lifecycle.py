class ModelLifecycle:
    def __init__(self, llm, embedder, mode='resident'):
        self.llm, self.embedder, self.mode = llm, embedder, mode
        self.llm.before_load = lambda: self.select('llm')
        self.embedder.before_load = lambda: self.select('embeddings')

    def select(self, component):
        target = self.llm if component == 'llm' else self.embedder
        other = self.embedder if component == 'llm' else self.llm
        if getattr(target,'model',None) is not None:
            return
        if self.mode == 'alternating':
            if getattr(other, 'model', True) is not None:
                other.unload()
        elif getattr(other,'model',None) is not None and not getattr(target,'factory',None):
            settings = getattr(target,'settings',None)
            if not settings:
                return
            try:
                from pathlib import Path
                directory = settings.models_dir / component
                if component == 'llm':
                    weights = directory / settings.model_filename
                else:
                    weights = next((p for p in directory.iterdir() if p.name in {'model.safetensors','pytorch_model.bin'}),None)
                if not weights or not weights.exists():
                    return
                device = settings.llm_backend if component == 'llm' else settings.embedding_device
                if device == 'cuda':
                    import torch
                    free,_ = torch.cuda.mem_get_info()
                else:
                    import psutil
                    free = psutil.virtual_memory().available
                # Conservative lower-bound heuristic, never a published hardware requirement.
                if free < weights.stat().st_size + 1024**3:
                    other.unload()
                    self.last_eviction = 'Outro modelo liberado por memória disponível limitada.'
            except (OSError,RuntimeError,ImportError):
                pass  # Backend's own load error remains explicit and never changes device.

    def close(self):
        self.llm.unload()
        self.embedder.unload()
