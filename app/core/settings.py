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
