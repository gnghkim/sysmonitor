# SysMonitor — Design Spec
*Date: 2026-06-20*

## Overview

Windows용 네이티브 시스템 성능 모니터링 도구. CPU/메모리/배터리/디스크/네트워크/온도를 실시간으로 보여주고, 전체 프로세스 목록에서 불필요한 프로세스(특히 Node.js)를 강제 종료할 수 있다. Python + customtkinter 기반으로 `.exe` 단일 파일과 소스 코드 두 가지 방식으로 배포한다.

---

## Goals

- 시스템 성능 지표를 실시간으로 한눈에 파악
- Node.js 프로세스 및 전체 프로세스를 목록으로 확인하고 강제 종료
- 다른 PC에서도 Python 없이 `.exe`로 바로 실행 가능
- 갱신 주기(기본 5초) 사용자 조절 가능

## Non-Goals

- macOS / Linux 지원 (Windows 전용)
- 원격 모니터링 (로컬 전용)
- 프로세스 시작 기능 (종료만 지원)
- 히스토리 데이터 영구 저장

---

## Architecture

```
sysmonitor/
├── main.py                  # 앱 진입점, customtkinter App 초기화
├── requirements.txt
├── build.spec               # PyInstaller 패키징 설정
└── app/
    ├── ui/
    │   ├── main_window.py   # CTk 메인 윈도우, 탭 컨테이너
    │   ├── tab_overview.py  # 시스템 개요 탭 (그래프 + 수치)
    │   ├── tab_processes.py # 프로세스 관리 탭 (테이블 + 종료)
    │   └── tab_settings.py  # 설정 탭 (갱신 주기, 테마)
    ├── core/
    │   ├── collector.py     # 백그라운드 스레드, psutil/wmi 수집
    │   └── killer.py        # 프로세스 강제 종료 및 권한 처리
    └── models/
        └── system_stats.py  # 수집 데이터 dataclass 정의
```

### 데이터 흐름

```
[백그라운드 스레드 - collector.py]
  └─ 매 N초마다 psutil/wmi 수집
  └─ SystemStats dataclass 생성
  └─ queue.Queue에 put()

[UI 스레드 - main_window.py]
  └─ after(500ms) 폴링으로 Queue에서 get()
  └─ 각 탭에 데이터 전달 → 화면 갱신
```

tkinter는 멀티스레드에 안전하지 않으므로 Queue를 통해 스레드 간 통신. UI 업데이트는 반드시 메인 스레드에서만 수행.

---

## Components

### collector.py

- `threading.Thread` 기반 데몬 스레드
- 수집 항목:
  - CPU: 전체 사용률(%), 코어별 사용률(%), 주파수(MHz)
  - 메모리: 사용량/전체(GB), 사용률(%)
  - 배터리: 잔량(%), 충전 상태, 예상 잔여시간(분)
  - 디스크: 읽기/쓰기 속도(MB/s) — 이전 수집값과의 델타로 계산
  - 네트워크: 업/다운 속도(MB/s) — 델타 계산
  - 온도: CPU 온도(°C), `wmi` 사용. 미지원 하드웨어는 `None` 반환
  - 프로세스: PID, 이름, CPU(%), 메모리(MB), 커맨드라인 전체
- 갱신 주기는 `settings.json`에서 읽어 동적으로 변경 가능

### system_stats.py

```python
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
    processes: list[ProcessInfo]

@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    mem_mb: float
    cmdline: str
```

### tab_overview.py

- 상단: CPU%, 메모리%, 배터리% 프로그레스바 + 수치 텍스트
- 중단: matplotlib Figure를 `FigureCanvasTkAgg`로 임베딩
  - CPU 사용률 라인 그래프 (최근 60포인트 = 기본 5분)
  - 메모리 사용률 라인 그래프
- 하단: 배터리 상태, 디스크 I/O, 네트워크, 온도 수치 표시

### tab_processes.py

- 검색창: 프로세스 이름 실시간 필터
- `[Node.js만 보기]` 토글 체크박스
- `ttk.Treeview` (customtkinter 내장 테이블 없음, ttk 위젯 혼용)
  - 컬럼: NAME / PID / CPU% / MEM(MB) / COMMAND
  - 헤더 클릭 정렬
- 행 선택 시 하단에 전체 커맨드라인 표시
- `[강제 종료]` 버튼 + `Delete` 키 바인딩
- 종료 전 확인 다이얼로그 (프로세스명 표시)
- 권한 오류 시 에러 메시지 표시

### killer.py

```python
def kill_process(pid: int) -> tuple[bool, str]:
    # psutil.Process(pid).kill()
    # 성공: (True, "")
    # 실패: (False, 에러 메시지)
```

- `NoSuchProcess`: 이미 종료된 프로세스
- `AccessDenied`: 관리자 권한 필요 안내
- 시스템 보호 프로세스(`System`, `csrss.exe` 등) 종료 시도 시 사전 경고

### tab_settings.py

- 갱신 주기: 1 / 2 / 5 / 10 / 30 / 60초 라디오 버튼 (기본: 5초)
- 테마: Dark / Light 토글
- 시작 탭: Overview / Processes 선택
- 변경 즉시 `settings.json` 저장

### settings.json (예시)

```json
{
  "refresh_interval": 5,
  "theme": "dark",
  "start_tab": "overview"
}
```

저장 위치: 실행 파일과 같은 디렉토리 (`.exe` 이식성 유지).

---

## UI Layout

```
┌─────────────────────────────────────────────────────┐
│ SysMonitor          [CPU 23%] [RAM 61%] [BAT 55%]   │
├──────────┬─────────────┬───────────────────────────┤
│ Overview │  Processes  │  Settings                  │
├──────────┴─────────────┴───────────────────────────┤
│                                                     │
│  [Overview]                                         │
│  CPU  ████░░░░░░ 23%                                │
│  RAM  ██████░░░░ 61%      [라인 그래프]              │
│  BAT  █████░░░░░ 55% · 방전중 · 잔여 60분           │
│  온도 52°C  |  디스크 R:12 W:3 MB/s                 │
│  네트워크 ↑0.3 ↓1.2 MB/s                           │
│                                                     │
│  [Processes]                                        │
│  🔍 [검색...]        [Node.js만 보기 ☑]             │
│  NAME      PID   CPU%  MEM(MB)  COMMAND             │
│  node.exe  13164  12%   150     nest start --watch  │
│  node.exe  21736   2%   107     playwright mcp...   │
│  ─────────────────────────────────────────          │
│  > node.exe (PID 13164)                             │
│    C:\Dev\Yield\backend\node_modules\...            │
│  [강제 종료]                                        │
└─────────────────────────────────────────────────────┘
```

윈도우 크기: 기본 900×650, 최소 700×500.

---

## Tech Stack

| 역할 | 라이브러리 | 버전 |
|------|-----------|------|
| UI | customtkinter | ≥5.2 |
| 시스템 정보 | psutil | ≥6.0 |
| 온도 (Windows) | wmi + pywin32 | ≥1.5 |
| 그래프 | matplotlib | ≥3.8 |
| 패키징 | pyinstaller | ≥6.0 |

---

## Error Handling

- **배터리 없음**: `psutil.sensors_battery()` → `None` 시 배터리 섹션 숨김
- **온도 미지원**: `wmi` 쿼리 실패 시 "N/A" 표시, 앱 계속 동작
- **프로세스 사라짐**: 목록 조회 중 프로세스 종료 시 해당 항목만 스킵
- **종료 권한 없음**: `AccessDenied` 시 "관리자 권한이 필요합니다" 다이얼로그

---

## Distribution

### 소스 배포
```bash
git clone <repo>
pip install -r requirements.txt
python main.py
```

### .exe 빌드
```bash
pyinstaller build.spec
# → dist/SysMonitor.exe (~40~60MB)
```

`build.spec`에 포함:
- customtkinter 테마 디렉토리
- matplotlib 폰트/데이터
- `--onefile --windowed` 옵션
