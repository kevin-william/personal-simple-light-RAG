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


def test_delivery_uses_token_counts_instead_of_chunk_count(monkeypatch):
    from src.ui.console import format_metrics
    monkeypatch.setattr('src.metrics.gpu_memory',lambda:None)
    clock=iter([0.,2.,4.,5.])
    metrics=Metrics(clock=lambda:next(clock),collector=lambda:None)
    metrics.start()
    metrics.mark_model_fragment('several tokens in one fragment')
    metrics.mark_model_fragment('more tokens')
    metrics.llm_calls=1
    report=metrics.finish(token_count=12,first_fragment_tokens=8)
    assert report['delivery_seconds']==2
    assert report['delivery_tokens_per_second_estimate']==2
    assert report['median_delivery_gap_seconds']==2
    # No native timings: never label the derived estimate as native decode.
    assert 'Decode nativo: indisponível' in format_metrics(report)


def test_latest_text_buffer_coalesces_every_fragment():
    from src.ui.streaming import TextBuffer
    buffer=TextBuffer()
    for text in ['a','b','c']:
        buffer.append(text)
    assert buffer.read(changed_only=True)=='abc'
    assert buffer.read(changed_only=True) is None
    buffer.append('d')
    assert buffer.read()=='abcd'
