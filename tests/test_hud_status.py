"""Tests for daemon/hud_status.py — the one-line HUD summary (mode/budget,
TODO counts, latest worklog insight) shared by SQUEEZER_HOME's statusLine,
`/squeezer:status`, and the Telegram message header."""
import importlib.util
import json
from pathlib import Path

import pytest

SQUEEZER_DIR = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location("hud_status", SQUEEZER_DIR / "daemon" / "hud_status.py")
hud_status = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hud_status)


@pytest.fixture(autouse=True)
def _isolate_usage_lib_state(tmp_path, monkeypatch):
    """usage_lib.STATE_PATH is a module-level constant resolved once at
    import time (see test_usage_lib.py's window_state_path fixture, which
    works around the same thing) — without this, current_status_line()'s
    call into usage_lib would read/write the real SQUEEZER_HOME's
    state/window_budget.json instead of this test's scratch one."""
    monkeypatch.setattr(hud_status.usage_lib, "STATE_PATH", tmp_path / "window_budget.json")


# --- build_status_line: pure assembly, no I/O ---

def test_build_status_line_includes_all_ranked_fragments():
    line = hud_status.build_status_line(
        mode="auto", paused=False, window_percent=42.0,
        open_count=5, blocked_count=1, project_count=2,
        last_insight="fixed the flaky test",
    )
    assert "auto" in line
    assert "42% window" in line
    assert "5 open, 1 blocked (2 proj)" in line
    assert "fixed the flaky test" in line


def test_build_status_line_shows_paused():
    line = hud_status.build_status_line(
        mode="auto", paused=True, window_percent=None,
        open_count=0, blocked_count=0, project_count=0, last_insight=None,
    )
    assert "auto·paused" in line


def test_build_status_line_omits_window_percent_when_uncalibrated():
    line = hud_status.build_status_line(
        mode="human_in_loop", paused=False, window_percent=None,
        open_count=1, blocked_count=0, project_count=1, last_insight=None,
    )
    assert "window" not in line


def test_build_status_line_no_projects_registered():
    line = hud_status.build_status_line(
        mode="auto", paused=False, window_percent=None,
        open_count=0, blocked_count=0, project_count=0, last_insight=None,
    )
    assert "no projects registered" in line


def test_build_status_line_omits_blocked_when_zero():
    line = hud_status.build_status_line(
        mode="auto", paused=False, window_percent=None,
        open_count=3, blocked_count=0, project_count=1, last_insight=None,
    )
    assert "3 open (1 proj)" in line
    assert "blocked" not in line


def test_build_status_line_truncates_to_width():
    line = hud_status.build_status_line(
        mode="auto", paused=False, window_percent=99.0,
        open_count=5, blocked_count=1, project_count=2,
        last_insight="a very long worklog snippet that should get cut off",
        width=30,
    )
    assert len(line) == 30
    assert line.endswith("…")


# --- current_status_line: real I/O against a scratch SQUEEZER_HOME ---

def _write_config(tmp_path, **overrides):
    cfg = {"mode": "auto", **overrides}
    (tmp_path / "config.json").write_text(json.dumps(cfg))


def test_current_status_line_counts_todos_across_projects(tmp_path, monkeypatch):
    monkeypatch.setenv("SQUEEZER_HOME", str(tmp_path))
    monkeypatch.delenv("COLUMNS", raising=False)
    _write_config(tmp_path)
    (tmp_path / "todos" / "acme").mkdir(parents=True)
    (tmp_path / "todos" / "acme" / "TODO.md").write_text(
        "- [ ] open item one\n- [b] blocked item\n- [x] done item\n"
    )
    (tmp_path / "todos" / "beta").mkdir(parents=True)
    (tmp_path / "todos" / "beta" / "TODO.md").write_text("- [ ] another open item\n")
    # The cross-project summary file itself must not be double-counted.
    (tmp_path / "todos" / "TODO.md").write_text("- [ ] [acme] open item one\n")

    line = hud_status.current_status_line()
    assert "2 open, 1 blocked (2 proj)" in line


def test_current_status_line_reports_paused(tmp_path, monkeypatch):
    monkeypatch.setenv("SQUEEZER_HOME", str(tmp_path))
    monkeypatch.delenv("COLUMNS", raising=False)
    _write_config(tmp_path)
    (tmp_path / "state").mkdir(parents=True)
    (tmp_path / "state" / "paused").write_text("")

    assert "paused" in hud_status.current_status_line()


def test_current_status_line_includes_latest_worklog_insight(tmp_path, monkeypatch):
    monkeypatch.setenv("SQUEEZER_HOME", str(tmp_path))
    monkeypatch.delenv("COLUMNS", raising=False)
    _write_config(tmp_path)
    (tmp_path / "state").mkdir(parents=True)
    (tmp_path / "state" / "worklog.md").write_text(
        "# Worklog\n\n## 2026-08-21\n- old entry, ignore this one\n\n"
        "## 2026-08-27\n- an earlier entry from the same day\n"
        "- shipped the HUD status line feature\n"
    )

    assert "shipped the HUD status line feature" in hud_status.current_status_line()


def test_last_insight_returns_none_without_worklog(tmp_path, monkeypatch):
    monkeypatch.setenv("SQUEEZER_HOME", str(tmp_path))
    (tmp_path / "state").mkdir(parents=True)
    assert hud_status._last_insight() is None


def test_last_insight_picks_the_last_bullet_of_the_day_not_the_first(tmp_path, monkeypatch):
    monkeypatch.setenv("SQUEEZER_HOME", str(tmp_path))
    (tmp_path / "state").mkdir(parents=True)
    (tmp_path / "state" / "worklog.md").write_text(
        "## 2026-08-27\n"
        "- earliest entry of the day, appended first\n"
        "  - a sub-bullet elaborating on it, should be skipped\n"
        "- a later entry appended after the first one finished\n"
    )
    assert hud_status._last_insight() == "a later entry appended after the first one finished"


def test_last_insight_truncates_long_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("SQUEEZER_HOME", str(tmp_path))
    (tmp_path / "state").mkdir(parents=True)
    long_line = "x" * 100
    (tmp_path / "state" / "worklog.md").write_text(f"## 2026-08-27\n- {long_line}\n")
    insight = hud_status._last_insight(max_len=20)
    assert len(insight) == 20
    assert insight.endswith("…")
