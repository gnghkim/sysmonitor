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
