#!/usr/bin/env python3
"""Wires SQUEEZER_HOME's own Claude Code statusLine to hud_status.py, so
opening an interactive session at SQUEEZER_HOME shows squeezer's one-line
HUD (mode/budget, TODO counts, latest worklog insight) — the same line
`/squeezer:status` leads with and telegram_lib prepends to messages.
Invoked by `/squeezer:setup`; idempotent, and only ever touches the
"statusLine" key so a customized SQUEEZER_HOME/.claude/settings.json keeps
any other settings the user has added there. This is scoped to
SQUEEZER_HOME's own project settings, so it doesn't touch (or conflict
with) a global statusLine like claude-hud configured elsewhere.
"""
import json
import sys
from pathlib import Path


def statusline_block(plugin_root: str) -> dict:
    return {
        "type": "command",
        "command": f"python3 {plugin_root}/daemon/hud_status.py",
        "refreshInterval": 5,
    }


def install(squeezer_home: Path, plugin_root: str) -> Path:
    settings_path = squeezer_home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    settings["statusLine"] = statusline_block(plugin_root)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    return settings_path


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: install_statusline.py <squeezer_home> <plugin_root>", file=sys.stderr)
        sys.exit(1)
    result_path = install(Path(sys.argv[1]), sys.argv[2])
    print(f"statusLine installed: {result_path}")
