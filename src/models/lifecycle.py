from collections import deque
from functools import wraps
import time


class ModelLifecycle:
    def __init__(self, llm, embedder, mode='resident'):
        self.llm, self.embedder, self.mode = llm, embedder, mode
        self.events = deque(maxlen=256)
        self._reasons = {}
        for component, model in (('llm',llm),('embeddings',embedder)):
            for action in ('load','unload'):
                if hasattr(model,action):
                    self._instrument(component,model,action)
        self.llm.before_load = lambda: self.select('llm')
        self.embedder.before_load = lambda: self.select('embeddings')

    def _device(self, component):
        model = self.llm if component == 'llm' else self.embedder
        settings = getattr(model,'settings',None)
        return getattr(settings,'llm_backend' if component == 'llm' else 'embedding_device',None)

    def _instrument(self, component, model, action):
        original = getattr(model,action)
        @wraps(original)
        def call(*args,**kwargs):
            changed = (getattr(model,'model',None) is None) == (action == 'load')
            started = time.perf_counter()
            success = False
            try:
                result = original(*args,**kwargs)
                success = True
                return result
            finally:
                if changed:
                    event = dict(component=component,action=action,device=self._device(component),
                                 seconds=time.perf_counter()-started,success=success,
                                 reason=self._reasons.get(component,'requested'))
                    self.events.append(event)
                    metrics = getattr(model,'metrics',None)
                    if metrics is not None:
                        metrics.model_events.append(event)
        setattr(model,action,call)

    def _unload(self, component, reason):
        self._reasons[component] = reason
        try:
            (self.llm if component == 'llm' else self.embedder).unload()
        finally:
            self._reasons.pop(component,None)

    def select(self, component):
        target = self.llm if component == 'llm' else self.embedder
        other = self.embedder if component == 'llm' else self.llm
        other_component = 'embeddings' if component == 'llm' else 'llm'
        if getattr(target,'model',None) is not None:
            return
        if self.mode == 'alternating':
            if getattr(other, 'model', True) is not None:
                self._unload(other_component,'alternating')
        elif getattr(other,'model',None) is not None and not getattr(target,'factory',None):
            if self._device(component) != self._device(other_component):
                return
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
                    self._unload(other_component,'memory_pressure')
                    self.last_eviction = 'Outro modelo liberado por memória disponível limitada.'
            except (OSError,RuntimeError,ImportError):
                pass  # Backend's own load error remains explicit and never changes device.

    def close(self):
        try:
            self._unload('llm','shutdown')
        finally:
            self._unload('embeddings','shutdown')
