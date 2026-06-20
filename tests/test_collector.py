import queue
from unittest.mock import patch, MagicMock
from app.core.collector import Collector
from app.core.settings import AppSettings

def _make_mock_psutil():
    mock = MagicMock()
    mock.cpu_percent.return_value = 25.0
    mock.virtual_memory.return_value = MagicMock(
        used=8 * 1024**3, total=16 * 1024**3, percent=50.0
    )
    battery = MagicMock()
    battery.percent = 80.0
    battery.power_plugged = False
    battery.secsleft = 3600
    mock.sensors_battery.return_value = battery
    disk = MagicMock(read_bytes=0, write_bytes=0)
    mock.disk_io_counters.return_value = disk
    net = MagicMock(bytes_sent=0, bytes_recv=0)
    mock.net_io_counters.return_value = net
    mock.process_iter.return_value = []
    return mock

def test_collect_returns_system_stats():
    settings = AppSettings(refresh_interval=5)
    q = queue.Queue()
    mock_psutil = _make_mock_psutil()
    with patch("app.core.collector.psutil", mock_psutil):
        collector = Collector(q, settings)
        stats = collector._collect()
    assert stats.cpu_percent == 25.0
    assert stats.mem_percent == 50.0
    assert stats.battery_percent == 80.0
    assert stats.battery_charging is False

def test_collect_no_battery():
    settings = AppSettings()
    q = queue.Queue()
    mock_psutil = _make_mock_psutil()
    mock_psutil.sensors_battery.return_value = None
    with patch("app.core.collector.psutil", mock_psutil):
        collector = Collector(q, settings)
        stats = collector._collect()
    assert stats.battery_percent is None
    assert stats.battery_remaining_min is None

def test_collect_skips_inaccessible_processes():
    import psutil as real_psutil
    from unittest.mock import PropertyMock
    settings = AppSettings()
    q = queue.Queue()
    mock_psutil = _make_mock_psutil()

    good_proc = MagicMock()
    good_proc.info = {
        "pid": 42, "name": "node.exe", "cpu_percent": 5.0,
        "memory_info": MagicMock(rss=50 * 1024**2), "cmdline": ["node", "server.js"]
    }

    bad_proc = MagicMock()
    type(bad_proc).info = PropertyMock(side_effect=real_psutil.NoSuchProcess(pid=99))

    mock_psutil.process_iter.return_value = [bad_proc, good_proc]
    with patch("app.core.collector.psutil", mock_psutil):
        collector = Collector(q, settings)
        stats = collector._collect()
    assert len(stats.processes) == 1
    assert stats.processes[0].name == "node.exe"

def test_collector_is_daemon_thread():
    settings = AppSettings()
    q = queue.Queue()
    mock_psutil = _make_mock_psutil()
    with patch("app.core.collector.psutil", mock_psutil):
        collector = Collector(q, settings)
    assert collector.daemon is True
