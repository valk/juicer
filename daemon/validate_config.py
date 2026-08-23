#!/usr/bin/env python3
"""Validate SQUEEZER_HOME/config.json: paths exist, have git (auto-init if
not, since git init is safe/non-destructive and gives the agent an undo
mechanism before it ever touches the project), and the mode/human_in_loop/
telegram_verbosity settings are well-formed."""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_VALID_MODES = {"auto", "human_in_loop"}
_VALID_ASK_CADENCES = {"every_window_reset", "daily"}
_VALID_VERBOSITY = {"narrow", "full"}


def main(config_path: Path):
    with open(config_path) as f:
        config = json.load(f)

    reserve = config.get("reserve_percent", 20)
    if not isinstance(reserve, (int, float)) or not (0 <= reserve <= 90):
        print(f"error: reserve_percent ({reserve}) should be a number between 0 and 90", file=sys.stderr)
        sys.exit(1)

    no_reserve_hours = config.get("no_reserve_hours")
    if no_reserve_hours is not None:
        if not isinstance(no_reserve_hours, dict) or set(no_reserve_hours) != {"start", "end"}:
            print("error: no_reserve_hours must be an object with exactly 'start' and 'end' keys", file=sys.stderr)
            sys.exit(1)
        for key in ("start", "end"):
            try:
                datetime.strptime(no_reserve_hours[key], "%H:%M")
            except (ValueError, TypeError):
                print(f"error: no_reserve_hours.{key} ({no_reserve_hours[key]!r}) must be 24h HH:MM", file=sys.stderr)
                sys.exit(1)

    def check_smart_mode(smart_mode, where):
        if smart_mode is None:
            return
        if not isinstance(smart_mode, dict) or not set(smart_mode) <= {"enabled", "tasks_per_cycle"}:
            print(f"error: {where}.smart_mode must be an object with only 'enabled'/'tasks_per_cycle' keys", file=sys.stderr)
            sys.exit(1)
        if "enabled" in smart_mode and not isinstance(smart_mode["enabled"], bool):
            print(f"error: {where}.smart_mode.enabled must be a boolean", file=sys.stderr)
            sys.exit(1)
        if "tasks_per_cycle" in smart_mode:
            tasks = smart_mode["tasks_per_cycle"]
            if not isinstance(tasks, int) or isinstance(tasks, bool) or tasks < 1:
                print(f"error: {where}.smart_mode.tasks_per_cycle must be a positive integer", file=sys.stderr)
                sys.exit(1)

    check_smart_mode(config.get("smart_mode"), "top-level")

    mode = config.get("mode", "auto")
    if mode not in _VALID_MODES:
        print(f"error: mode ({mode!r}) must be one of {sorted(_VALID_MODES)}", file=sys.stderr)
        sys.exit(1)

    human_in_loop = config.get("human_in_loop")
    if human_in_loop is not None:
        if not isinstance(human_in_loop, dict) or not set(human_in_loop) <= {"ask_cadence"}:
            print("error: human_in_loop must be an object with only an 'ask_cadence' key", file=sys.stderr)
            sys.exit(1)
        cadence = human_in_loop.get("ask_cadence", "every_window_reset")
        if cadence not in _VALID_ASK_CADENCES:
            print(f"error: human_in_loop.ask_cadence ({cadence!r}) must be one of {sorted(_VALID_ASK_CADENCES)}", file=sys.stderr)
            sys.exit(1)
        if cadence == "daily" and not no_reserve_hours:
            print("error: human_in_loop.ask_cadence 'daily' requires no_reserve_hours to be configured "
                  "(the daily ask fires at no_reserve_hours.start)", file=sys.stderr)
            sys.exit(1)

    verbosity = config.get("telegram_verbosity", "narrow")
    if verbosity not in _VALID_VERBOSITY:
        print(f"error: telegram_verbosity ({verbosity!r}) must be one of {sorted(_VALID_VERBOSITY)}", file=sys.stderr)
        sys.exit(1)

    projects = config.get("projects", [])
    if not projects:
        print("error: config.json has no projects registered", file=sys.stderr)
        sys.exit(1)

    names = set()
    for p in projects:
        name, path = p["name"], Path(p["path"])
        if name in names:
            print(f"error: duplicate project name '{name}'", file=sys.stderr)
            sys.exit(1)
        names.add(name)
        check_smart_mode(p.get("smart_mode"), f"project '{name}'")

        if name.startswith("example-project"):
            print(f"error: '{name}' looks like an unedited placeholder from config.example.json — replace it", file=sys.stderr)
            sys.exit(1)

        if not path.is_dir():
            print(f"error: project '{name}' path does not exist: {path}", file=sys.stderr)
            sys.exit(1)

        if not (path / ".git").exists():
            print(f"'{name}' has no git history — running 'git init' as a safety net ({path})")
            subprocess.run(["git", "init"], cwd=path, check=True)

        print(f"ok: {name} -> {path}")

    print(f"validated {len(projects)} project(s), mode={mode}, reserve_percent={reserve}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
