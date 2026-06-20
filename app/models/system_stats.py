from dataclasses import dataclass, field

@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    mem_mb: float
    cmdline: str

@dataclass
class SystemStats:
    timestamp: float
    cpu_percent: float
    cpu_per_core: list[float]
    mem_used_gb: float
    mem_total_gb: float
    mem_percent: float
    battery_percent: float | None
    battery_charging: bool
    battery_remaining_min: int | None
    disk_read_mbps: float
    disk_write_mbps: float
    net_up_mbps: float
    net_down_mbps: float
    cpu_temp: float | None
    processes: list[ProcessInfo] = field(default_factory=list)
