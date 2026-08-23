---
description: Show squeezer's current daemon status — mode, pause state, budget, registered projects.
---

Report squeezer's current status. Use the Bash tool for each check below and
summarize concisely at the end — this is a status check, not a report.

1. `SQUEEZER_HOME="${SQUEEZER_HOME:-$HOME/.config/squeezer}"`.
2. Print the one-line HUD summary first: `python3 ${CLAUDE_PLUGIN_ROOT}/daemon/hud_status.py`. Then continue with the detailed report below.
3. Read `$SQUEEZER_HOME/config.json` and report the current `mode` and, if `human_in_loop`, its `ask_cadence`.
4. Report whether `$SQUEEZER_HOME/state/paused` exists (paused vs running).
5. `python3 ${CLAUDE_PLUGIN_ROOT}/daemon/usage_lib.py status` for the current window budget, and `... quiet-hours` for whether it's currently within `no_reserve_hours`.
6. List registered projects from `config.json`; for each, count open (`- [ ]`) vs blocked (`- [b]`) items in `$SQUEEZER_HOME/todos/<project>/TODO.md`.
7. Confirm the daemon service is actually running: macOS — `launchctl list | grep com.squeezer.daemon`; Linux — `systemctl --user status squeezer-daemon.service`.
