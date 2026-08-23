"""Tests for daemon/install_statusline.py — wiring SQUEEZER_HOME's own
Claude Code statusLine to hud_status.py, invoked by `/squeezer:setup`."""
import importlib.util
import json
from pathlib import Path

SQUEEZER_DIR = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "install_statusline", SQUEEZER_DIR / "daemon" / "install_statusline.py"
)
install_statusline = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(install_statusline)


def test_install_creates_settings_with_statusline(tmp_path):
    settings_path = install_statusline.install(tmp_path, "/plugin/root")
    assert settings_path == tmp_path / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text())
    assert settings["statusLine"]["type"] == "command"
    assert "/plugin/root/daemon/hud_status.py" in settings["statusLine"]["command"]
    assert settings["statusLine"]["refreshInterval"] == 5


def test_install_preserves_existing_unrelated_settings(tmp_path):
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"model": "sonnet"}))

    install_statusline.install(tmp_path, "/plugin/root")

    settings = json.loads(settings_path.read_text())
    assert settings["model"] == "sonnet"
    assert "statusLine" in settings


def test_install_is_idempotent_and_refreshes_plugin_root(tmp_path):
    install_statusline.install(tmp_path, "/old/root")
    install_statusline.install(tmp_path, "/new/root")

    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    assert "/new/root/daemon/hud_status.py" in settings["statusLine"]["command"]
    assert "/old/root" not in settings["statusLine"]["command"]
