"""Minimal tests for daemon/validate_config.py: no_reserve_hours validation
(unchanged from the old projects.json shape) plus the new mode/human_in_loop/
telegram_verbosity checks."""
import json
import subprocess
import sys
from pathlib import Path

SQUEEZER_DIR = Path(__file__).resolve().parent.parent
VALIDATE_SCRIPT = SQUEEZER_DIR / "daemon" / "validate_config.py"


def run_validate(tmp_path, data):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data))
    return subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), str(path)],
        capture_output=True,
        text=True,
    )


def test_bad_time_format_rejected(tmp_path):
    result = run_validate(tmp_path, {
        "reserve_percent": 20,
        "no_reserve_hours": {"start": "2am", "end": "07:00"},
        "projects": [],
    })
    assert result.returncode == 1
    assert "no_reserve_hours" in result.stderr


def test_missing_key_rejected(tmp_path):
    result = run_validate(tmp_path, {
        "reserve_percent": 20,
        "no_reserve_hours": {"start": "02:00"},
        "projects": [],
    })
    assert result.returncode == 1
    assert "no_reserve_hours" in result.stderr


def test_valid_window_passes_validation(tmp_path):
    result = run_validate(tmp_path, {
        "reserve_percent": 20,
        "no_reserve_hours": {"start": "02:00", "end": "07:00"},
        "projects": [],
    })
    # fails later, on the (unrelated) empty-projects check, proving
    # no_reserve_hours itself validated cleanly
    assert result.returncode == 1
    assert "no projects registered" in result.stderr
    assert "no_reserve_hours" not in result.stderr


def test_omitted_key_is_fine(tmp_path):
    result = run_validate(tmp_path, {"reserve_percent": 20, "projects": []})
    assert result.returncode == 1
    assert "no projects registered" in result.stderr


def test_smart_mode_omitted_is_fine(tmp_path):
    result = run_validate(tmp_path, {"reserve_percent": 20, "projects": []})
    assert "smart_mode" not in result.stderr


def test_smart_mode_bad_tasks_per_cycle_rejected(tmp_path):
    result = run_validate(tmp_path, {
        "reserve_percent": 20,
        "smart_mode": {"tasks_per_cycle": 0},
        "projects": [],
    })
    assert result.returncode == 1
    assert "smart_mode.tasks_per_cycle" in result.stderr


def test_smart_mode_bad_enabled_type_rejected(tmp_path):
    result = run_validate(tmp_path, {
        "reserve_percent": 20,
        "smart_mode": {"enabled": "yes"},
        "projects": [],
    })
    assert result.returncode == 1
    assert "smart_mode.enabled" in result.stderr


def test_smart_mode_unknown_key_rejected(tmp_path):
    result = run_validate(tmp_path, {
        "reserve_percent": 20,
        "smart_mode": {"typo_field": 3},
        "projects": [],
    })
    assert result.returncode == 1
    assert "smart_mode" in result.stderr


def test_smart_mode_valid_passes(tmp_path):
    result = run_validate(tmp_path, {
        "reserve_percent": 20,
        "smart_mode": {"enabled": True, "tasks_per_cycle": 3},
        "projects": [],
    })
    assert result.returncode == 1
    assert "no projects registered" in result.stderr
    assert "smart_mode" not in result.stderr


def test_smart_mode_per_project_override_validated(tmp_path):
    result = run_validate(tmp_path, {
        "reserve_percent": 20,
        "projects": [
            {"name": "demo", "path": str(tmp_path), "smart_mode": {"tasks_per_cycle": -1}},
        ],
    })
    assert result.returncode == 1
    assert "demo" in result.stderr and "smart_mode.tasks_per_cycle" in result.stderr


# --- mode / human_in_loop / telegram_verbosity ---

def test_unknown_mode_rejected(tmp_path):
    result = run_validate(tmp_path, {"reserve_percent": 20, "mode": "sleepwalking", "projects": []})
    assert result.returncode == 1
    assert "mode" in result.stderr


def test_default_mode_is_fine(tmp_path):
    result = run_validate(tmp_path, {"reserve_percent": 20, "projects": []})
    assert "mode" not in result.stderr


def test_human_in_loop_unknown_cadence_rejected(tmp_path):
    result = run_validate(tmp_path, {
        "reserve_percent": 20,
        "human_in_loop": {"ask_cadence": "hourly"},
        "projects": [],
    })
    assert result.returncode == 1
    assert "ask_cadence" in result.stderr


def test_human_in_loop_daily_requires_no_reserve_hours(tmp_path):
    result = run_validate(tmp_path, {
        "reserve_percent": 20,
        "no_reserve_hours": None,
        "human_in_loop": {"ask_cadence": "daily"},
        "projects": [],
    })
    assert result.returncode == 1
    assert "daily" in result.stderr


def test_human_in_loop_daily_with_no_reserve_hours_passes(tmp_path):
    result = run_validate(tmp_path, {
        "reserve_percent": 20,
        "no_reserve_hours": {"start": "23:00", "end": "07:00"},
        "human_in_loop": {"ask_cadence": "daily"},
        "projects": [],
    })
    assert result.returncode == 1
    assert "no projects registered" in result.stderr
    assert "ask_cadence" not in result.stderr


def test_unknown_telegram_verbosity_rejected(tmp_path):
    result = run_validate(tmp_path, {"reserve_percent": 20, "telegram_verbosity": "loud", "projects": []})
    assert result.returncode == 1
    assert "telegram_verbosity" in result.stderr
