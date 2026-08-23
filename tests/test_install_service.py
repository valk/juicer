"""Tests for daemon/install_service.py — the launchd (macOS) / systemd --user
(Linux) service generator that replaces bin/install_launchd.sh +
launchd/*.template. Only one process to supervise now (the daemon), not a
3-window tmux session. Real launchctl/systemctl calls are mocked out; only
the generation + file-writing logic is exercised."""
import importlib.util
from pathlib import Path

SQUEEZER_DIR = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "install_service", SQUEEZER_DIR / "daemon" / "install_service.py"
)
install_service = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(install_service)


def test_launchd_plist_contains_label_and_paths():
    plist = install_service.launchd_plist("/usr/bin/python3", Path("/opt/squeezer/daemon.py"), Path("/tmp/daemon.log"))
    assert install_service.LABEL in plist
    assert "/usr/bin/python3" in plist
    assert "/opt/squeezer/daemon.py" in plist
    assert "/tmp/daemon.log" in plist
    assert "<key>RunAtLoad</key>" in plist


def test_launchd_plist_keeps_alive():
    plist = install_service.launchd_plist("/usr/bin/python3", Path("/opt/daemon.py"), Path("/tmp/x.log"))
    assert "<key>KeepAlive</key>" in plist


def test_systemd_unit_contains_exec_and_restart():
    unit = install_service.systemd_unit("/usr/bin/python3", Path("/opt/squeezer/daemon.py"))
    assert "ExecStart=/usr/bin/python3 /opt/squeezer/daemon.py" in unit
    assert "Restart=always" in unit


def test_install_unsupported_platform(monkeypatch):
    monkeypatch.setattr(install_service.platform, "system", lambda: "Windows")
    result = install_service.install()
    assert result["ok"] is False
    assert "unsupported" in result["error"].lower()


def test_install_macos_writes_plist_and_loads(tmp_path, monkeypatch):
    plist_path = tmp_path / "LaunchAgents" / f"{install_service.LABEL}.plist"
    monkeypatch.setattr(install_service, "launchd_plist_path", lambda: plist_path)
    monkeypatch.setattr(install_service.platform, "system", lambda: "Darwin")

    calls = []
    monkeypatch.setattr(install_service.subprocess, "run", lambda cmd, **k: calls.append(cmd))

    result = install_service.install(python_bin="/usr/bin/python3", squeezer_home=tmp_path)

    assert result["ok"] is True
    assert plist_path.exists()
    assert "/usr/bin/python3" in plist_path.read_text()
    assert any(c[:2] == ["launchctl", "load"] for c in calls)


def test_install_linux_writes_unit_and_enables(tmp_path, monkeypatch):
    unit_path = tmp_path / "systemd" / "user" / "squeezer-daemon.service"
    monkeypatch.setattr(install_service, "systemd_unit_path", lambda: unit_path)
    monkeypatch.setattr(install_service.platform, "system", lambda: "Linux")

    calls = []
    monkeypatch.setattr(install_service.subprocess, "run", lambda cmd, **k: calls.append(cmd))

    result = install_service.install(python_bin="/usr/bin/python3", squeezer_home=tmp_path)

    assert result["ok"] is True
    assert unit_path.exists()
    assert any("enable" in c for c in calls)


def test_uninstall_macos_removes_plist(tmp_path, monkeypatch):
    plist_path = tmp_path / f"{install_service.LABEL}.plist"
    plist_path.write_text("dummy")
    monkeypatch.setattr(install_service, "launchd_plist_path", lambda: plist_path)
    monkeypatch.setattr(install_service.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(install_service.subprocess, "run", lambda *a, **k: None)

    result = install_service.uninstall()
    assert result["ok"] is True
    assert not plist_path.exists()


def test_uninstall_unsupported_platform(monkeypatch):
    monkeypatch.setattr(install_service.platform, "system", lambda: "Windows")
    result = install_service.uninstall()
    assert result["ok"] is False
