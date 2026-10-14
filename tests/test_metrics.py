from src.metrics import Metrics,measured


def test_timing_null_memory_and_zero_duration(monkeypatch):
    monkeypatch.setattr('src.metrics.gpu_memory',lambda:None)
    clock = iter([0.,1.,2.,3.,4.])
    metrics = Metrics(clock=lambda:next(clock),collector=lambda:None)
    metrics.start()
    with metrics.phase('search'):
        pass
    metrics.mark_token()
    report = metrics.finish(0)
    assert report['phase_seconds']['search'] == 1
    assert report['ttft_seconds'] == 3
    assert report['peak_rss_bytes'] is None and report['process_vram_mib_at_end'] is None
    assert report['tokens_per_second'] is None


def test_instrumentation_preserves_return():
    class Service:
        metrics = Metrics(collector=lambda:100)
        @measured('test')
        def call(self):
            return 'result'
    s = Service()
    assert s.call() == 'result'
    assert s.metrics.peak_rss == 100 and 'test' in s.metrics.durations
