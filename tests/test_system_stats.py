from app.models.system_stats import SystemStats, ProcessInfo

def test_process_info_creation():
    p = ProcessInfo(pid=123, name="node.exe", cpu_percent=5.0, mem_mb=150.0, cmdline="node server.js")
    assert p.pid == 123
    assert p.name == "node.exe"
    assert p.cpu_percent == 5.0

def test_system_stats_creation():
    stats = SystemStats(
        timestamp=1.0, cpu_percent=23.0, cpu_per_core=[20.0, 26.0],
        mem_used_gb=8.0, mem_total_gb=16.0, mem_percent=50.0,
        battery_percent=80.0, battery_charging=False, battery_remaining_min=90,
        disk_read_mbps=5.0, disk_write_mbps=1.0,
        net_up_mbps=0.1, net_down_mbps=1.5,
        cpu_temp=52.0, processes=[]
    )
    assert stats.cpu_percent == 23.0
    assert stats.mem_percent == 50.0
    assert stats.processes == []

def test_system_stats_no_battery():
    stats = SystemStats(
        timestamp=1.0, cpu_percent=50.0, cpu_per_core=[50.0],
        mem_used_gb=4.0, mem_total_gb=8.0, mem_percent=50.0,
        battery_percent=None, battery_charging=False, battery_remaining_min=None,
        disk_read_mbps=0.0, disk_write_mbps=0.0,
        net_up_mbps=0.0, net_down_mbps=0.0,
        cpu_temp=None, processes=[]
    )
    assert stats.battery_percent is None
    assert stats.cpu_temp is None
