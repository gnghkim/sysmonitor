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
