#!/usr/bin/env python3
"""Cross-platform installer for squeezer's daemon as an always-on OS
service — launchd on macOS, systemd --user on Linux. Replaces
bin/install_launchd.sh + launchd/*.template: there's only one process to
supervise now (daemon.py), not a 3-window tmux session, so the service just
needs to keep that one process alive across crashes/reboots. Invoked by the
`/squeezer:setup` command, not run directly during normal operation.
"""
import platform
import subprocess
import sys
from pathlib import Path

LABEL = "com.squeezer.daemon"
DAEMON_SCRIPT = Path(__file__).resolve().parent / "daemon.py"


def launchd_plist(python_bin: str, daemon_script: Path, log_path: Path) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{python_bin}</string>
    <string>{daemon_script}</string>
  </array>
  <key>KeepAlive</key>
  <true/>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>{log_path}</string>
  <key>StandardErrorPath</key>
  <string>{log_path}</string>
</dict>
</plist>
"""


def systemd_unit(python_bin: str, daemon_script: Path) -> str:
    return f"""[Unit]
Description=squeezer endless-loop orchestrator daemon

[Service]
ExecStart={python_bin} {daemon_script}
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
"""


def launchd_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def systemd_unit_path() -> Path:
    return Path.home() / ".config" / "systemd" / "user" / "squeezer-daemon.service"


def install(python_bin: str = None, squeezer_home: Path = None) -> dict:
    """Writes and enables the appropriate service file for this OS. Returns
    {"ok": bool, "path": str} or {"ok": False, "error": str}."""
    python_bin = python_bin or sys.executable
    squeezer_home = squeezer_home or (Path.home() / ".config" / "squeezer")
    system = platform.system()

    if system == "Darwin":
        path = launchd_plist_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        log_path = squeezer_home / "state" / "daemon.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(launchd_plist(python_bin, DAEMON_SCRIPT, log_path))
        subprocess.run(["launchctl", "unload", str(path)], check=False, capture_output=True)
        subprocess.run(["launchctl", "load", str(path)], check=True, capture_output=True)
        return {"ok": True, "path": str(path)}

    if system == "Linux":
        path = systemd_unit_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(systemd_unit(python_bin, DAEMON_SCRIPT))
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True, capture_output=True)
        subprocess.run(["systemctl", "--user", "enable", "--now", path.stem + ".service"], check=True, capture_output=True)
        return {"ok": True, "path": str(path)}

    return {"ok": False, "error": f"unsupported platform: {system} (only macOS and Linux are supported)"}


def uninstall() -> dict:
    system = platform.system()

    if system == "Darwin":
        path = launchd_plist_path()
        if path.exists():
            subprocess.run(["launchctl", "unload", str(path)], check=False, capture_output=True)
            path.unlink()
        return {"ok": True}

    if system == "Linux":
        path = systemd_unit_path()
        subprocess.run(["systemctl", "--user", "disable", "--now", path.stem + ".service"], check=False, capture_output=True)
        if path.exists():
            path.unlink()
        return {"ok": True}

    return {"ok": False, "error": f"unsupported platform: {system} (only macOS and Linux are supported)"}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "install"
    if cmd == "install":
        result = install()
    elif cmd == "uninstall":
        result = uninstall()
    else:
        print("usage: install_service.py {install|uninstall}", file=sys.stderr)
        sys.exit(1)
    print(result)
    if not result.get("ok"):
        sys.exit(1)
