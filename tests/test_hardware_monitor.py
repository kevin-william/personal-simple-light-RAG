import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock
from src.models.hardware import get_resource_snapshot, NvmlClient, get_nvml_client
from src.ui.tui import ResourceMonitorWidget, RagTuiApp
from tests.test_pipeline import build


def test_resource_snapshot_structure():
    snapshot = get_resource_snapshot()
    assert isinstance(snapshot, dict)
    expected_keys = {
        'cpu_percent', 'ram_used_gb', 'ram_total_gb', 'ram_percent',
        'process_rss_mb', 'gpu_available', 'gpu_name', 'gpu_util',
        'vram_used_mib', 'vram_total_mib', 'vram_percent', 'gpu_temp_c'
    }
    assert expected_keys.issubset(set(snapshot.keys()))
    assert snapshot['ram_total_gb'] > 0
    assert 0.0 <= snapshot['ram_percent'] <= 100.0
    assert snapshot['process_rss_mb'] >= 0.0


def test_resource_snapshot_fallback_without_gpu(monkeypatch):
    mock_client = MagicMock()
    mock_client.get_metrics.return_value = None
    monkeypatch.setattr('src.models.hardware.get_nvml_client', lambda: mock_client)

    snapshot = get_resource_snapshot()
    assert snapshot['gpu_available'] is False
    assert snapshot['gpu_name'] == 'N/A (CPU)'
    assert snapshot['gpu_util'] is None
    assert snapshot['vram_used_mib'] is None


def test_resource_monitor_widget_rendering_and_dirty_check():
    widget = ResourceMonitorWidget()
    fake_snapshot = {
        'cpu_percent': 15.5,
        'ram_used_gb': 8.0,
        'ram_total_gb': 16.0,
        'ram_percent': 50.0,
        'process_rss_mb': 120.5,
        'gpu_available': True,
        'gpu_name': 'NVIDIA Test GPU',
        'gpu_util': 25,
        'vram_used_mib': 2048,
        'vram_total_mib': 6144,
        'vram_percent': 33.3,
        'gpu_temp_c': 50
    }
    widget.update_metrics(fake_snapshot)
    rendered_text = widget._last_content
    assert '15.5%' in rendered_text
    assert '120.5 MB' in rendered_text
    assert 'NVIDIA Test GPU' in rendered_text
    assert '2048 / 6144 MiB (33.3%)' in rendered_text
    assert '#00ff66' in rendered_text  # VRAM < 80% é verde

    # Testa dirty check (não altera se chamar com mesmos valores)
    widget.update_metrics(fake_snapshot)
    assert widget._last_content == rendered_text

    # Testa threshold de cor do VRAM > 90%
    fake_snapshot_high = dict(fake_snapshot, vram_percent=92.0)
    widget.update_metrics(fake_snapshot_high)
    assert '#ff3333' in widget._last_content


@pytest.mark.anyio
async def test_tui_hardware_monitor_integration(tmp_path):
    pipeline = build(tmp_path)
    mock_sources = []
    catalog = SimpleNamespace(list_sources=lambda: mock_sources)
    rag_app = SimpleNamespace(pipeline=pipeline, catalog=catalog)

    app = RagTuiApp(rag_app)
    async with app.run_test(size=(140, 50)) as pilot:
        monitor = app.query_one('#resource-monitor', ResourceMonitorWidget)
        assert monitor is not None
        await pilot.pause(0.2)
        assert app._monitor_running is True
