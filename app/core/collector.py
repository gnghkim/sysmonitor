import queue
import threading
import time
import psutil
from psutil import NoSuchProcess, AccessDenied
from app.core.settings import AppSettings
from app.models.system_stats import ProcessInfo, SystemStats


class Collector(threading.Thread):
    def __init__(self, data_queue: queue.Queue, settings: AppSettings):
        super().__init__(daemon=True)
        self._queue = data_queue
        self._settings = settings
        self._stop_event = threading.Event()
        self._prev_disk = None
        self._prev_net = None
        self._prev_time: float | None = None

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            stats = self._collect()
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            self._queue.put(stats)
            self._stop_event.wait(self._settings.refresh_interval)

    def _collect(self) -> SystemStats:
        now = time.time()

        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_per_core: list[float] = psutil.cpu_percent(percpu=True)  # type: ignore[assignment]

        mem = psutil.virtual_memory()

        battery = psutil.sensors_battery()
        battery_percent: float | None = battery.percent if battery else None
        battery_charging: bool = battery.power_plugged if battery else False
        battery_remaining_min: int | None = None
        if battery and not battery.power_plugged and battery.secsleft > 0:
            battery_remaining_min = int(battery.secsleft / 60)

        disk_io = psutil.disk_io_counters()
        disk_read_mbps = 0.0
        disk_write_mbps = 0.0
        if self._prev_disk and self._prev_time:
            dt = now - self._prev_time
            if dt > 0:
                disk_read_mbps = max(0.0, (disk_io.read_bytes - self._prev_disk.read_bytes) / dt / (1024**2))
                disk_write_mbps = max(0.0, (disk_io.write_bytes - self._prev_disk.write_bytes) / dt / (1024**2))
        self._prev_disk = disk_io

        net_io = psutil.net_io_counters()
        net_up_mbps = 0.0
        net_down_mbps = 0.0
        if self._prev_net and self._prev_time:
            dt = now - self._prev_time
            if dt > 0:
                net_up_mbps = max(0.0, (net_io.bytes_sent - self._prev_net.bytes_sent) / dt / (1024**2))
                net_down_mbps = max(0.0, (net_io.bytes_recv - self._prev_net.bytes_recv) / dt / (1024**2))
        self._prev_net = net_io
        self._prev_time = now

        return SystemStats(
            timestamp=now,
            cpu_percent=cpu_percent,
            cpu_per_core=cpu_per_core,
            mem_used_gb=mem.used / (1024**3),
            mem_total_gb=mem.total / (1024**3),
            mem_percent=mem.percent,
            battery_percent=battery_percent,
            battery_charging=battery_charging,
            battery_remaining_min=battery_remaining_min,
            disk_read_mbps=disk_read_mbps,
            disk_write_mbps=disk_write_mbps,
            net_up_mbps=net_up_mbps,
            net_down_mbps=net_down_mbps,
            cpu_temp=self._get_cpu_temp(),
            processes=self._get_processes(),
        )

    def _get_cpu_temp(self) -> float | None:
        try:
            import wmi  # noqa: PLC0415
            w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            for s in w.Sensor():
                if s.SensorType == "Temperature" and "CPU" in s.Name:
                    return float(s.Value)
        except Exception:
            pass
        try:
            import wmi  # noqa: PLC0415
            w = wmi.WMI(namespace="root\\wmi")
            temps = w.MSAcpi_ThermalZoneTemperature()
            if temps:
                return round((temps[0].CurrentTemperature / 10.0) - 273.15, 1)
        except Exception:
            pass
        return None

    def _get_processes(self) -> list[ProcessInfo]:
        result: list[ProcessInfo] = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "cmdline"]):
            try:
                info = proc.info
                cmdline = " ".join(info["cmdline"]) if info["cmdline"] else (info["name"] or "")
                result.append(ProcessInfo(
                    pid=info["pid"],
                    name=info["name"] or "",
                    cpu_percent=info["cpu_percent"] or 0.0,
                    mem_mb=(info["memory_info"].rss / (1024**2)) if info["memory_info"] else 0.0,
                    cmdline=cmdline,
                ))
            except (NoSuchProcess, AccessDenied):
                continue
        return result
