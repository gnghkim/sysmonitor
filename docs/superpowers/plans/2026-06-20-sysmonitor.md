# SysMonitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Windows용 네이티브 시스템 모니터링 앱 — CPU/메모리/배터리/디스크/네트워크/온도를 실시간으로 표시하고 프로세스를 강제 종료할 수 있는 customtkinter 데스크탑 앱

**Architecture:** 백그라운드 스레드(Collector)가 psutil로 데이터를 수집해 queue.Queue에 넣고, UI 메인 스레드가 500ms마다 폴링해서 화면을 갱신한다. UI는 Overview / Processes / Settings 3개 탭으로 구성된다.

**Tech Stack:** Python 3.11+, customtkinter≥5.2, psutil≥6.0, wmi+pywin32, matplotlib≥3.8, PyInstaller≥6.0, pytest≥8.0

## Global Constraints

- Python 3.11 이상 필수 (`float | None` 타입 유니언 문법 사용)
- Windows 전용 (wmi는 Windows 전용 라이브러리)
- UI 업데이트는 반드시 메인 스레드에서만 수행 (tkinter 스레드 제약)
- settings.json은 실행 파일(또는 main.py)과 같은 디렉토리에 저장
- 모든 프로세스 종료 전 확인 다이얼로그 필수
- 시스템 보호 프로세스(system, csrss.exe 등)는 종료 불가

---

## File Map

```
sysmonitor/
├── main.py                        # 앱 진입점
├── requirements.txt               # 런타임 의존성
├── requirements-dev.txt           # 테스트 의존성
├── build.spec                     # PyInstaller 설정
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── system_stats.py        # SystemStats, ProcessInfo dataclass
│   ├── core/
│   │   ├── __init__.py
│   │   ├── settings.py            # AppSettings, load/save
│   │   ├── collector.py           # 백그라운드 수집 스레드
│   │   └── killer.py              # 프로세스 강제 종료
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py         # CTk 메인 윈도우, 탭 컨테이너
│       ├── tab_overview.py        # 시스템 개요 탭
│       ├── tab_processes.py       # 프로세스 관리 탭
│       └── tab_settings.py        # 설정 탭
└── tests/
    ├── __init__.py
    ├── test_system_stats.py
    ├── test_settings.py
    ├── test_killer.py
    └── test_collector.py
```

---

### Task 1: 프로젝트 스캐폴딩

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `app/__init__.py`, `app/models/__init__.py`, `app/core/__init__.py`, `app/ui/__init__.py`
- Create: `tests/__init__.py`

**Interfaces:**
- Produces: 설치 가능한 의존성 환경

- [ ] **Step 1: 디렉토리 생성**

```powershell
New-Item -ItemType Directory -Force app/models, app/core, app/ui, tests
```

- [ ] **Step 2: requirements.txt 작성**

```
customtkinter>=5.2.2
psutil>=6.0.0
wmi>=1.5.1
pywin32>=306
matplotlib>=3.8.0
```

- [ ] **Step 3: requirements-dev.txt 작성**

```
pytest>=8.0
```

- [ ] **Step 4: __init__.py 파일 생성**

아래 경로 각각에 빈 파일 생성:
- `app/__init__.py`
- `app/models/__init__.py`
- `app/core/__init__.py`
- `app/ui/__init__.py`
- `tests/__init__.py`

- [ ] **Step 5: 의존성 설치**

```powershell
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Expected: 에러 없이 설치 완료. `pip show customtkinter psutil matplotlib` 확인.

- [ ] **Step 6: Commit**

```bash
git init
git add .
git commit -m "chore: project scaffolding"
```

---

### Task 2: 데이터 모델

**Files:**
- Create: `app/models/system_stats.py`
- Test: `tests/test_system_stats.py`

**Interfaces:**
- Produces:
  - `ProcessInfo(pid: int, name: str, cpu_percent: float, mem_mb: float, cmdline: str)`
  - `SystemStats(timestamp, cpu_percent, cpu_per_core, mem_used_gb, mem_total_gb, mem_percent, battery_percent, battery_charging, battery_remaining_min, disk_read_mbps, disk_write_mbps, net_up_mbps, net_down_mbps, cpu_temp, processes)`

- [ ] **Step 1: 테스트 작성**

`tests/test_system_stats.py`:
```python
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
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```powershell
pytest tests/test_system_stats.py -v
```

Expected: `ImportError: cannot import name 'SystemStats'`

- [ ] **Step 3: 모델 구현**

`app/models/system_stats.py`:
```python
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
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```powershell
pytest tests/test_system_stats.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add app/models/system_stats.py tests/test_system_stats.py
git commit -m "feat: add SystemStats and ProcessInfo dataclasses"
```

---

### Task 3: Settings 관리자

**Files:**
- Create: `app/core/settings.py`
- Test: `tests/test_settings.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `AppSettings(refresh_interval: int = 5, theme: str = "dark", start_tab: str = "overview")`
  - `load_settings() -> AppSettings`
  - `save_settings(settings: AppSettings) -> None`
  - `_settings_path() -> str`  ← 테스트에서 monkeypatch 대상

- [ ] **Step 1: 테스트 작성**

`tests/test_settings.py`:
```python
import json
from app.core.settings import AppSettings, load_settings, save_settings
import app.core.settings as settings_module

def test_default_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(settings_module, "_settings_path", lambda: str(tmp_path / "settings.json"))
    s = load_settings()
    assert s.refresh_interval == 5
    assert s.theme == "dark"
    assert s.start_tab == "overview"

def test_save_and_load(tmp_path, monkeypatch):
    path = str(tmp_path / "settings.json")
    monkeypatch.setattr(settings_module, "_settings_path", lambda: path)
    original = AppSettings(refresh_interval=10, theme="light", start_tab="processes")
    save_settings(original)
    loaded = load_settings()
    assert loaded.refresh_interval == 10
    assert loaded.theme == "light"
    assert loaded.start_tab == "processes"

def test_corrupted_json_falls_back_to_defaults(tmp_path, monkeypatch):
    path = str(tmp_path / "settings.json")
    monkeypatch.setattr(settings_module, "_settings_path", lambda: path)
    with open(path, "w") as f:
        f.write("{ invalid json }")
    s = load_settings()
    assert s.refresh_interval == 5

def test_save_creates_valid_json(tmp_path, monkeypatch):
    path = str(tmp_path / "settings.json")
    monkeypatch.setattr(settings_module, "_settings_path", lambda: path)
    save_settings(AppSettings(refresh_interval=30, theme="dark", start_tab="overview"))
    with open(path) as f:
        data = json.load(f)
    assert data["refresh_interval"] == 30
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```powershell
pytest tests/test_settings.py -v
```

Expected: `ImportError`

- [ ] **Step 3: settings.py 구현**

`app/core/settings.py`:
```python
import json
import os
import sys
from dataclasses import dataclass, asdict

@dataclass
class AppSettings:
    refresh_interval: int = 5
    theme: str = "dark"
    start_tab: str = "overview"

def _settings_path() -> str:
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "settings.json")

def load_settings() -> AppSettings:
    path = _settings_path()
    if not os.path.exists(path):
        return AppSettings()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return AppSettings(
            refresh_interval=int(data.get("refresh_interval", 5)),
            theme=str(data.get("theme", "dark")),
            start_tab=str(data.get("start_tab", "overview")),
        )
    except (json.JSONDecodeError, ValueError, KeyError):
        return AppSettings()

def save_settings(settings: AppSettings) -> None:
    path = _settings_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(settings), f, indent=2)
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```powershell
pytest tests/test_settings.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add app/core/settings.py tests/test_settings.py
git commit -m "feat: add settings load/save"
```

---

### Task 4: 프로세스 종료 (killer)

**Files:**
- Create: `app/core/killer.py`
- Test: `tests/test_killer.py`

**Interfaces:**
- Consumes: `psutil`
- Produces:
  - `kill_process(pid: int) -> tuple[bool, str]`  — 성공: `(True, "")`, 실패: `(False, 에러메시지)`
  - `is_protected(name: str) -> bool`

- [ ] **Step 1: 테스트 작성**

`tests/test_killer.py`:
```python
from unittest.mock import patch, MagicMock
import psutil
from app.core.killer import kill_process, is_protected

def test_is_protected_known_system_processes():
    assert is_protected("csrss.exe") is True
    assert is_protected("SYSTEM") is True
    assert is_protected("lsass.exe") is True
    assert is_protected("smss.exe") is True

def test_is_protected_normal_process():
    assert is_protected("node.exe") is False
    assert is_protected("chrome.exe") is False

def test_kill_success():
    mock_proc = MagicMock()
    mock_proc.name.return_value = "node.exe"
    with patch("app.core.killer.psutil.Process", return_value=mock_proc):
        ok, msg = kill_process(12345)
    assert ok is True
    assert msg == ""
    mock_proc.kill.assert_called_once()

def test_kill_no_such_process():
    with patch("app.core.killer.psutil.Process", side_effect=psutil.NoSuchProcess(pid=99)):
        ok, msg = kill_process(99)
    assert ok is False
    assert "이미 종료" in msg

def test_kill_access_denied():
    mock_proc = MagicMock()
    mock_proc.name.return_value = "node.exe"
    mock_proc.kill.side_effect = psutil.AccessDenied(pid=1)
    with patch("app.core.killer.psutil.Process", return_value=mock_proc):
        ok, msg = kill_process(1)
    assert ok is False
    assert "관리자 권한" in msg

def test_kill_protected_process_is_blocked():
    mock_proc = MagicMock()
    mock_proc.name.return_value = "csrss.exe"
    with patch("app.core.killer.psutil.Process", return_value=mock_proc):
        ok, msg = kill_process(4)
    assert ok is False
    assert "보호" in msg
    mock_proc.kill.assert_not_called()
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```powershell
pytest tests/test_killer.py -v
```

Expected: `ImportError`

- [ ] **Step 3: killer.py 구현**

`app/core/killer.py`:
```python
import psutil

_PROTECTED = {"system", "csrss.exe", "smss.exe", "wininit.exe", "lsass.exe", "services.exe"}

def is_protected(name: str) -> bool:
    return name.lower() in _PROTECTED

def kill_process(pid: int) -> tuple[bool, str]:
    try:
        proc = psutil.Process(pid)
        if is_protected(proc.name()):
            return False, f"'{proc.name()}'은(는) 시스템 보호 프로세스입니다."
        proc.kill()
        return True, ""
    except psutil.NoSuchProcess:
        return False, "프로세스가 이미 종료되었습니다."
    except psutil.AccessDenied:
        return False, "권한이 없습니다. 관리자 권한으로 실행해주세요."
    except Exception as e:
        return False, str(e)
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```powershell
pytest tests/test_killer.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add app/core/killer.py tests/test_killer.py
git commit -m "feat: add process killer with protected-process guard"
```

---

### Task 5: 데이터 수집기 (collector)

**Files:**
- Create: `app/core/collector.py`
- Test: `tests/test_collector.py`

**Interfaces:**
- Consumes:
  - `AppSettings` from `app.core.settings`
  - `SystemStats`, `ProcessInfo` from `app.models.system_stats`
- Produces:
  - `Collector(data_queue: queue.Queue, settings: AppSettings)` — `threading.Thread` 서브클래스
  - `collector.stop()` — 스레드 정지
  - `collector._collect() -> SystemStats` — 단위 테스트용 내부 메서드

- [ ] **Step 1: 테스트 작성**

`tests/test_collector.py`:
```python
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
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```powershell
pytest tests/test_collector.py -v
```

Expected: `ImportError`

- [ ] **Step 3: collector.py 구현**

`app/core/collector.py`:
```python
import queue
import threading
import time
import psutil
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
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return result
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```powershell
pytest tests/test_collector.py -v
```

Expected: `4 passed`

- [ ] **Step 5: 전체 테스트 통과 확인**

```powershell
pytest tests/ -v
```

Expected: `14 passed` (이전 태스크 포함)

- [ ] **Step 6: Commit**

```bash
git add app/core/collector.py tests/test_collector.py
git commit -m "feat: add background data collector with psutil"
```

---

### Task 6: Overview 탭

**Files:**
- Create: `app/ui/tab_overview.py`

**Interfaces:**
- Consumes: `SystemStats` from `app.models.system_stats`
- Produces: `OverviewTab(parent)` — `ctk.CTkFrame` 서브클래스, `update(stats: SystemStats) -> None`

- [ ] **Step 1: tab_overview.py 작성**

`app/ui/tab_overview.py`:
```python
from collections import deque
import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from app.models.system_stats import SystemStats

MAX_POINTS = 60


class OverviewTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cpu_history: deque[float] = deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
        self._mem_history: deque[float] = deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
        self._build_ui()

    def _build_ui(self):
        metrics = ctk.CTkFrame(self)
        metrics.pack(fill="x", padx=10, pady=(10, 5))
        metrics.columnconfigure(1, weight=1)

        self._cpu_bar, self._cpu_lbl = self._make_bar(metrics, "CPU", 0)
        self._mem_bar, self._mem_lbl = self._make_bar(metrics, "RAM", 1)
        self._bat_bar, self._bat_lbl = self._make_bar(metrics, "Battery", 2)

        fig = Figure(figsize=(8, 3), dpi=90, facecolor="#1e1e1e")
        self._ax_cpu = fig.add_subplot(2, 1, 1)
        self._ax_mem = fig.add_subplot(2, 1, 2)
        self._style_ax(self._ax_cpu, "CPU %")
        self._style_ax(self._ax_mem, "RAM %")
        self._line_cpu, = self._ax_cpu.plot(list(self._cpu_history), color="#4fc3f7", linewidth=1.5)
        self._line_mem, = self._ax_mem.plot(list(self._mem_history), color="#81c784", linewidth=1.5)
        fig.tight_layout(pad=1.2)

        self._canvas = FigureCanvasTkAgg(fig, master=self)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=5)

        stats_row = ctk.CTkFrame(self, fg_color="transparent")
        stats_row.pack(fill="x", padx=10, pady=(5, 10))
        self._lbl_temp = ctk.CTkLabel(stats_row, text="온도: --")
        self._lbl_temp.pack(side="left", padx=10)
        self._lbl_disk = ctk.CTkLabel(stats_row, text="디스크: --")
        self._lbl_disk.pack(side="left", padx=10)
        self._lbl_net = ctk.CTkLabel(stats_row, text="네트워크: --")
        self._lbl_net.pack(side="left", padx=10)
        self._lbl_bat_detail = ctk.CTkLabel(stats_row, text="")
        self._lbl_bat_detail.pack(side="right", padx=10)

    def _make_bar(self, parent, label: str, row: int) -> tuple:
        ctk.CTkLabel(parent, text=label, width=70, anchor="w").grid(
            row=row, column=0, padx=(10, 5), pady=4, sticky="w"
        )
        bar = ctk.CTkProgressBar(parent)
        bar.grid(row=row, column=1, padx=5, pady=4, sticky="ew")
        bar.set(0)
        lbl = ctk.CTkLabel(parent, text="0%", width=55, anchor="e")
        lbl.grid(row=row, column=2, padx=(5, 10), pady=4)
        return bar, lbl

    def _style_ax(self, ax, ylabel: str):
        ax.set_facecolor("#2b2b2b")
        ax.set_xlim(0, MAX_POINTS)
        ax.set_ylim(0, 100)
        ax.set_ylabel(ylabel, color="#aaaaaa", fontsize=8)
        ax.tick_params(colors="#aaaaaa", labelsize=7)
        for spine in ax.spines.values():
            spine.set_color("#444444")

    def update(self, stats: SystemStats):
        self._cpu_history.append(stats.cpu_percent)
        self._mem_history.append(stats.mem_percent)

        self._cpu_bar.set(stats.cpu_percent / 100)
        self._cpu_lbl.configure(text=f"{stats.cpu_percent:.0f}%")

        self._mem_bar.set(stats.mem_percent / 100)
        self._mem_lbl.configure(text=f"{stats.mem_percent:.0f}%")

        if stats.battery_percent is not None:
            self._bat_bar.set(stats.battery_percent / 100)
            self._bat_lbl.configure(text=f"{stats.battery_percent:.0f}%")
            status = "충전중" if stats.battery_charging else "방전중"
            remain = f" · 잔여 {stats.battery_remaining_min}분" if stats.battery_remaining_min else ""
            self._lbl_bat_detail.configure(text=f"배터리 {status}{remain}")
        else:
            self._bat_bar.set(0)
            self._bat_lbl.configure(text="N/A")

        self._line_cpu.set_ydata(list(self._cpu_history))
        self._line_mem.set_ydata(list(self._mem_history))
        self._canvas.draw_idle()

        temp_str = f"온도: {stats.cpu_temp:.0f}°C" if stats.cpu_temp is not None else "온도: N/A"
        self._lbl_temp.configure(text=temp_str)
        self._lbl_disk.configure(
            text=f"디스크  R:{stats.disk_read_mbps:.1f}  W:{stats.disk_write_mbps:.1f} MB/s"
        )
        self._lbl_net.configure(
            text=f"↑{stats.net_up_mbps:.2f}  ↓{stats.net_down_mbps:.2f} MB/s"
        )
```

- [ ] **Step 2: 수동 스모크 테스트**

`main.py`를 아직 작성하지 않았으므로 임시 스크립트로 확인:

```python
# 터미널에서 실행: python -c "..."
import customtkinter as ctk
from app.ui.tab_overview import OverviewTab
from app.models.system_stats import SystemStats

ctk.set_appearance_mode("dark")
root = ctk.CTk()
root.geometry("900x600")
tab = OverviewTab(root)
tab.pack(fill="both", expand=True)

dummy = SystemStats(
    timestamp=1.0, cpu_percent=42.0, cpu_per_core=[40.0, 44.0],
    mem_used_gb=8.0, mem_total_gb=16.0, mem_percent=50.0,
    battery_percent=75.0, battery_charging=False, battery_remaining_min=90,
    disk_read_mbps=5.2, disk_write_mbps=1.1,
    net_up_mbps=0.3, net_down_mbps=1.2,
    cpu_temp=52.0, processes=[]
)
tab.update(dummy)
root.mainloop()
```

Expected: 창이 열리고, 프로그레스바·그래프·수치가 표시됨.

- [ ] **Step 3: Commit**

```bash
git add app/ui/tab_overview.py
git commit -m "feat: add Overview tab with real-time graphs"
```

---

### Task 7: Processes 탭

**Files:**
- Create: `app/ui/tab_processes.py`

**Interfaces:**
- Consumes:
  - `list[ProcessInfo]` from `app.models.system_stats`
  - `kill_process(pid: int) -> tuple[bool, str]` from `app.core.killer`
  - `is_protected(name: str) -> bool` from `app.core.killer`
- Produces: `ProcessesTab(parent)` — `ctk.CTkFrame` 서브클래스, `update(processes: list[ProcessInfo]) -> None`

- [ ] **Step 1: tab_processes.py 작성**

`app/ui/tab_processes.py`:
```python
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from app.core.killer import is_protected, kill_process
from app.models.system_stats import ProcessInfo


class ProcessesTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._all_processes: list[ProcessInfo] = []
        self._sort_attr = "cpu_percent"
        self._sort_reverse = True
        self._node_only = tk.BooleanVar(value=False)
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh_table())
        self._build_ui()

    def _build_ui(self):
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkEntry(toolbar, textvariable=self._search_var,
                     placeholder_text="검색...", width=200).pack(side="left")
        ctk.CTkCheckBox(toolbar, text="Node.js만 보기",
                        variable=self._node_only, command=self._refresh_table).pack(side="left", padx=12)

        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="#eeeeee",
                        fieldbackground="#2b2b2b", rowheight=24, font=("Consolas", 9))
        style.configure("Treeview.Heading", background="#3b3b3b", foreground="#cccccc",
                        relief="flat", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#1f538d")])

        cols = ("name", "pid", "cpu", "mem", "cmd")
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")

        col_defs = [
            ("name", "NAME", 130),
            ("pid", "PID", 65),
            ("cpu", "CPU%", 65),
            ("mem", "MEM(MB)", 85),
            ("cmd", "COMMAND", 400),
        ]
        for col_id, label, width in col_defs:
            self._tree.heading(col_id, text=label, command=lambda c=col_id: self._sort_by(c))
            self._tree.column(col_id, width=width, minwidth=40, stretch=(col_id == "cmd"))

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._tree.tag_configure("node", foreground="#4fc3f7")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Delete>", lambda _: self._kill_selected())

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=10, pady=(5, 10))
        self._lbl_cmd = ctk.CTkLabel(bottom, text="", anchor="w", wraplength=680)
        self._lbl_cmd.pack(side="left", fill="x", expand=True)
        self._btn_kill = ctk.CTkButton(
            bottom, text="강제 종료", width=100,
            fg_color="#c0392b", hover_color="#922b21",
            command=self._kill_selected, state="disabled",
        )
        self._btn_kill.pack(side="right")

    def update(self, processes: list[ProcessInfo]):
        self._all_processes = processes
        self._refresh_table()

    def _filtered(self) -> list[ProcessInfo]:
        search = self._search_var.get().lower()
        result = self._all_processes
        if self._node_only.get():
            result = [p for p in result if "node" in p.name.lower()]
        if search:
            result = [p for p in result if search in p.name.lower() or search in p.cmdline.lower()]
        return sorted(result, key=lambda p: getattr(p, self._sort_attr), reverse=self._sort_reverse)

    def _refresh_table(self):
        selected_pid = self._selected_pid()
        self._tree.delete(*self._tree.get_children())
        for proc in self._filtered():
            tag = "node" if "node" in proc.name.lower() else ""
            self._tree.insert("", "end", iid=str(proc.pid), tags=(tag,), values=(
                proc.name,
                proc.pid,
                f"{proc.cpu_percent:.1f}",
                f"{proc.mem_mb:.1f}",
                proc.cmdline[:100],
            ))
        if selected_pid and self._tree.exists(str(selected_pid)):
            self._tree.selection_set(str(selected_pid))

    def _selected_pid(self) -> int | None:
        sel = self._tree.selection()
        return int(sel[0]) if sel else None

    def _on_select(self, _event=None):
        pid = self._selected_pid()
        if pid is None:
            self._lbl_cmd.configure(text="")
            self._btn_kill.configure(state="disabled")
            return
        proc = next((p for p in self._all_processes if p.pid == pid), None)
        if proc:
            self._lbl_cmd.configure(text=proc.cmdline)
            protected = is_protected(proc.name)
            self._btn_kill.configure(state="disabled" if protected else "normal")

    def _kill_selected(self):
        pid = self._selected_pid()
        if pid is None:
            return
        proc = next((p for p in self._all_processes if p.pid == pid), None)
        name = proc.name if proc else f"PID {pid}"
        if not messagebox.askyesno("강제 종료 확인", f"'{name}' (PID {pid})을(를) 강제 종료하시겠습니까?"):
            return
        ok, msg = kill_process(pid)
        if ok:
            self._tree.delete(str(pid))
            self._lbl_cmd.configure(text="")
            self._btn_kill.configure(state="disabled")
        else:
            messagebox.showerror("종료 실패", msg)

    def _sort_by(self, col: str):
        attr_map = {
            "name": "name", "pid": "pid",
            "cpu": "cpu_percent", "mem": "mem_mb", "cmd": "cmdline",
        }
        attr = attr_map[col]
        if self._sort_attr == attr:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_attr = attr
            self._sort_reverse = attr in ("cpu_percent", "mem_mb")
        self._refresh_table()
```

- [ ] **Step 2: 수동 스모크 테스트**

```python
import customtkinter as ctk
from app.ui.tab_processes import ProcessesTab
from app.models.system_stats import ProcessInfo

ctk.set_appearance_mode("dark")
root = ctk.CTk()
root.geometry("900x500")
tab = ProcessesTab(root)
tab.pack(fill="both", expand=True)

procs = [
    ProcessInfo(pid=1000, name="node.exe", cpu_percent=12.3, mem_mb=150.0,
                cmdline="node C:\\Dev\\backend\\node_modules\\.bin\\nest start --watch"),
    ProcessInfo(pid=2000, name="chrome.exe", cpu_percent=5.1, mem_mb=300.0, cmdline="chrome.exe"),
    ProcessInfo(pid=3000, name="node.exe", cpu_percent=2.1, mem_mb=107.0, cmdline="node playwright.js"),
]
tab.update(procs)
root.mainloop()
```

Expected: 테이블에 3개 프로세스 표시, node.exe는 파란색, 검색·필터·정렬 동작 확인.

- [ ] **Step 3: Commit**

```bash
git add app/ui/tab_processes.py
git commit -m "feat: add Processes tab with kill and filter"
```

---

### Task 8: Settings 탭

**Files:**
- Create: `app/ui/tab_settings.py`

**Interfaces:**
- Consumes: `AppSettings` from `app.core.settings`
- Produces: `SettingsTab(parent, settings: AppSettings, on_change: Callable[[AppSettings], None])`

- [ ] **Step 1: tab_settings.py 작성**

`app/ui/tab_settings.py`:
```python
from typing import Callable
import customtkinter as ctk
from app.core.settings import AppSettings

INTERVALS = [1, 2, 5, 10, 30, 60]


class SettingsTab(ctk.CTkFrame):
    def __init__(self, parent, settings: AppSettings, on_change: Callable[[AppSettings], None]):
        super().__init__(parent, fg_color="transparent")
        self._on_change = on_change
        self._interval_var = ctk.IntVar(value=settings.refresh_interval)
        self._theme_var = ctk.StringVar(value=settings.theme)
        self._start_tab_var = ctk.StringVar(value=settings.start_tab)
        self._build_ui()

    def _build_ui(self):
        section_font = ctk.CTkFont(size=13, weight="bold")
        pad = {"padx": 24, "pady": (16, 6)}

        ctk.CTkLabel(self, text="갱신 주기", font=section_font).pack(anchor="w", **pad)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(anchor="w", padx=24, pady=(0, 8))
        for val in INTERVALS:
            ctk.CTkRadioButton(
                row, text=f"{val}초", variable=self._interval_var,
                value=val, command=self._save,
            ).pack(side="left", padx=8)

        ctk.CTkLabel(self, text="테마", font=section_font).pack(anchor="w", **pad)
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(anchor="w", padx=24, pady=(0, 8))
        for val, label in [("dark", "Dark"), ("light", "Light")]:
            ctk.CTkRadioButton(
                row2, text=label, variable=self._theme_var,
                value=val, command=self._save,
            ).pack(side="left", padx=8)

        ctk.CTkLabel(self, text="시작 탭", font=section_font).pack(anchor="w", **pad)
        row3 = ctk.CTkFrame(self, fg_color="transparent")
        row3.pack(anchor="w", padx=24, pady=(0, 8))
        for val, label in [("overview", "Overview"), ("processes", "Processes")]:
            ctk.CTkRadioButton(
                row3, text=label, variable=self._start_tab_var,
                value=val, command=self._save,
            ).pack(side="left", padx=8)

    def _save(self):
        self._on_change(AppSettings(
            refresh_interval=self._interval_var.get(),
            theme=self._theme_var.get(),
            start_tab=self._start_tab_var.get(),
        ))
```

- [ ] **Step 2: Commit**

```bash
git add app/ui/tab_settings.py
git commit -m "feat: add Settings tab"
```

---

### Task 9: 메인 윈도우 & 진입점

**Files:**
- Create: `app/ui/main_window.py`
- Create: `main.py`

**Interfaces:**
- Consumes: 모든 탭 컴포넌트, `Collector`, `AppSettings`
- Produces: 실행 가능한 앱

- [ ] **Step 1: main_window.py 작성**

`app/ui/main_window.py`:
```python
import queue
import customtkinter as ctk
from app.core.collector import Collector
from app.core.settings import AppSettings, load_settings, save_settings
from app.ui.tab_overview import OverviewTab
from app.ui.tab_processes import ProcessesTab
from app.ui.tab_settings import SettingsTab


class MainWindow(ctk.CTk):
    def __init__(self):
        self._settings = load_settings()
        ctk.set_appearance_mode(self._settings.theme)
        ctk.set_default_color_theme("blue")
        super().__init__()

        self.title("SysMonitor")
        self.geometry("900x650")
        self.minsize(700, 500)

        self._queue: queue.Queue = queue.Queue(maxsize=1)
        self._collector = Collector(self._queue, self._settings)

        self._build_ui()
        self._collector.start()
        self._poll()

    def _build_ui(self):
        self._tabs = ctk.CTkTabview(self)
        self._tabs.pack(fill="both", expand=True, padx=10, pady=10)

        for name in ("Overview", "Processes", "Settings"):
            self._tabs.add(name)

        self._overview = OverviewTab(self._tabs.tab("Overview"))
        self._overview.pack(fill="both", expand=True)

        self._processes = ProcessesTab(self._tabs.tab("Processes"))
        self._processes.pack(fill="both", expand=True)

        self._settings_tab = SettingsTab(
            self._tabs.tab("Settings"),
            self._settings,
            on_change=self._apply_settings,
        )
        self._settings_tab.pack(fill="both", expand=True)

        start = "Overview" if self._settings.start_tab == "overview" else "Processes"
        self._tabs.set(start)

    def _poll(self):
        try:
            stats = self._queue.get_nowait()
            self._overview.update(stats)
            self._processes.update(stats.processes)
        except queue.Empty:
            pass
        self.after(500, self._poll)

    def _apply_settings(self, new: AppSettings):
        self._settings = new
        save_settings(new)
        self._collector._settings = new
        ctk.set_appearance_mode(new.theme)

    def on_closing(self):
        self._collector.stop()
        self.destroy()
```

- [ ] **Step 2: main.py 작성**

`main.py`:
```python
from app.ui.main_window import MainWindow

if __name__ == "__main__":
    app = MainWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
```

- [ ] **Step 3: 앱 실행 확인**

```powershell
python main.py
```

Expected:
- 다크 테마 창(900×650) 열림
- Overview 탭: 프로그레스바와 그래프가 5초마다 갱신됨
- Processes 탭: 프로세스 목록 표시, 검색·Node.js 필터 동작
- Settings 탭: 갱신 주기 변경 시 즉시 적용

- [ ] **Step 4: Commit**

```bash
git add app/ui/main_window.py main.py
git commit -m "feat: wire up main window and app entry point"
```

---

### Task 10: PyInstaller 빌드 설정

**Files:**
- Create: `build.spec`

**Interfaces:**
- Consumes: `main.py` 및 모든 앱 파일
- Produces: `dist/SysMonitor.exe` 단일 실행 파일

- [ ] **Step 1: build.spec 작성**

`build.spec`:
```python
import os
import customtkinter
import matplotlib

block_cipher = None

ctk_path = os.path.dirname(customtkinter.__file__)
mpl_data = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        (ctk_path, "customtkinter"),
        (mpl_data, "matplotlib/mpl-data"),
    ],
    hiddenimports=[
        "customtkinter",
        "matplotlib",
        "matplotlib.backends.backend_tkagg",
        "psutil",
        "wmi",
        "win32api",
        "win32con",
        "pywintypes",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SysMonitor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

- [ ] **Step 2: 빌드 실행**

```powershell
pyinstaller build.spec
```

Expected: `dist/SysMonitor.exe` 생성 (40~80MB). 빌드 로그에 `ERROR` 없이 완료.

- [ ] **Step 3: exe 동작 확인**

```powershell
.\dist\SysMonitor.exe
```

Expected: `python main.py`와 동일하게 동작. `settings.json`이 exe 옆에 생성됨.

- [ ] **Step 4: .gitignore 추가**

`.gitignore`:
```
__pycache__/
*.pyc
dist/
build/
*.spec.bak
settings.json
```

- [ ] **Step 5: Commit**

```bash
git add build.spec .gitignore
git commit -m "chore: add PyInstaller build spec and .gitignore"
```

---

## 전체 테스트 최종 확인

모든 태스크 완료 후:

```powershell
pytest tests/ -v
```

Expected: `14 passed`, `0 failed`
