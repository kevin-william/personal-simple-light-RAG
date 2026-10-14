from contextlib import contextmanager, nullcontext
from functools import wraps
import time
import threading
import subprocess
import os


def process_rss():
    try:
        import psutil
        return psutil.Process().memory_info().rss
    except (ImportError,OSError,RuntimeError):
        return None


def gpu_memory():
    # NVIDIA WDDM may report N/A for process VRAM; do not replace it with zero.
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    try:
        result = subprocess.run(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],
                                capture_output=True,text=True,timeout=3,creationflags=flags)
        values = []
        for line in result.stdout.splitlines():
            pid,memory = [part.strip() for part in line.split(',',1)]
            if pid == str(os.getpid()):
                values.append(float(memory))
        return sum(values) if values else None
    except (OSError,ValueError,subprocess.TimeoutExpired):
        return None


class Metrics:
    def __init__(self,clock=time.perf_counter,collector=process_rss):
        self.clock,self.collector = clock,collector
        self.reset()

    def reset(self):
        self.durations = {}
        self.started = self.first_token = self.generation_started = self.generation_finished = None
        self.peak_rss = None
        self._stop = threading.Event()
        self._thread = None

    def sample(self):
        try:
            value = self.collector()
        except Exception:
            value = None
        if value is not None:
            self.peak_rss = max(self.peak_rss or 0,value)

    def start(self):
        self.reset()
        self.started = self.clock()
        def sample_loop():
            while not self._stop.wait(.1):
                self.sample()
        self.sample()
        self._thread = threading.Thread(target=sample_loop,daemon=True)
        self._thread.start()

    @contextmanager
    def phase(self,name):
        start = self.clock()
        try:
            yield
        finally:
            self.durations[name] = self.durations.get(name,0.) + max(0.,self.clock()-start)
            self.sample()

    def mark_token(self):
        if self.first_token is None:
            self.first_token = self.clock()

    def finish(self,token_count=0):
        ended = self.clock()
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=.3)
        self.sample()
        generation_seconds = (self.generation_finished-self.generation_started) if self.generation_finished is not None else None
        return {'total_seconds':max(0.,ended-self.started) if self.started is not None else None,
                'ttft_seconds':max(0.,self.first_token-self.started) if self.first_token is not None and self.started is not None else None,
                'generation_seconds':generation_seconds,
                'generated_tokens':token_count,
                'tokens_per_second':token_count/generation_seconds if generation_seconds and generation_seconds>0 else None,
                'phase_seconds':dict(self.durations), 'peak_rss_bytes':self.peak_rss,
                'process_vram_mib_at_end':gpu_memory()}


def measured(name,predicate=None):
    def decorate(function):
        @wraps(function)
        def wrapped(self,*args,**kwargs):
            metrics = getattr(self,'metrics',None)
            if predicate and not predicate(self):
                metrics = None
            with metrics.phase(name) if metrics else nullcontext():
                return function(self,*args,**kwargs)
        return wrapped
    return decorate
