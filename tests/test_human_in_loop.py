"""Tests for daemon/human_in_loop.py's decision engine — the branching that
decides, once per daemon tick, whether human-in-loop mode should proceed
automatically, ask the human what to do next, or sit idle. Pure functions,
no I/O: every input the branching depends on is passed in explicitly."""
import importlib.util
from datetime import datetime, time
from pathlib import Path

SQUEEZER_DIR = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "human_in_loop", SQUEEZER_DIR / "daemon" / "human_in_loop.py"
)
human_in_loop = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(human_in_loop)

Action = human_in_loop.Action
decide_action = human_in_loop.decide_action

NIGHT_START = time(23, 0)
DAY = datetime(2026, 8, 27, 14, 0)          # 2pm — daytime
NIGHT = datetime(2026, 8, 27, 23, 30)       # 11:30pm — inside night hours
JUST_BEFORE_NIGHT = datetime(2026, 8, 27, 22, 59)


def _decide(**overrides):
    defaults = dict(
        mode="human_in_loop",
        ask_cadence="every_window_reset",
        now=DAY,
        is_night=False,
        night_start=NIGHT_START,
        window_start_ts="2026-08-27T10:00:00+00:00",
        state={},
        budget_cap_reached=False,
    )
    defaults.update(overrides)
    return decide_action(**defaults)


# --- mode gate ---

def test_auto_mode_always_continues_regardless_of_everything_else():
    assert _decide(mode="auto", state={"awaiting_reply": True}, budget_cap_reached=True) == Action.AUTO_CONTINUE


# --- every_window_reset cadence ---

def test_fresh_window_not_yet_asked_sends_ask():
    assert _decide(state={"last_asked_window_start": "some-older-window"}) == Action.SEND_ASK


def test_same_window_already_asked_and_awaiting_goes_idle():
    state = {"last_asked_window_start": "2026-08-27T10:00:00+00:00", "awaiting_reply": True}
    assert _decide(state=state) == Action.IDLE


def test_same_window_already_answered_continues_automatically():
    state = {"last_asked_window_start": "2026-08-27T10:00:00+00:00", "awaiting_reply": False}
    assert _decide(state=state) == Action.AUTO_CONTINUE


def test_every_window_reset_ask_suppressed_at_night():
    # A fresh window during the night should NOT prompt — night behavior
    # always wins for this cadence.
    assert _decide(
        now=NIGHT, is_night=True,
        state={"last_asked_window_start": "older-window"},
    ) == Action.AUTO_CONTINUE


def test_night_ignores_awaiting_reply_and_budget_cap():
    # Never disturbed at night, and never blocked either — auto mode
    # overrides both a pending question and a hit budget cap.
    state = {"last_asked_window_start": "2026-08-27T10:00:00+00:00", "awaiting_reply": True}
    assert _decide(now=NIGHT, is_night=True, state=state, budget_cap_reached=True) == Action.AUTO_CONTINUE


# --- daily cadence ---

def test_daily_cadence_no_ask_before_night_start():
    state = {"last_asked_date": "2026-08-26"}
    assert _decide(ask_cadence="daily", now=JUST_BEFORE_NIGHT, state=state) == Action.IDLE \
        or _decide(ask_cadence="daily", now=JUST_BEFORE_NIGHT, state=state) == Action.AUTO_CONTINUE
    # not yet due -> never SEND_ASK before the boundary
    assert _decide(ask_cadence="daily", now=JUST_BEFORE_NIGHT, state=state) != Action.SEND_ASK


def test_daily_cadence_fires_exactly_at_night_start():
    state = {"last_asked_date": "2026-08-26"}  # asked yesterday, not yet today
    assert _decide(ask_cadence="daily", now=NIGHT, is_night=True, state=state) == Action.SEND_ASK


def test_daily_cadence_does_not_reask_same_day():
    state = {"last_asked_date": "2026-08-27"}
    assert _decide(ask_cadence="daily", now=NIGHT, is_night=True, state=state) == Action.AUTO_CONTINUE


def test_daily_cadence_after_asking_falls_through_to_auto_at_night_even_unanswered():
    # Fire-and-forget: the ask isn't blocking, night behavior takes over
    # immediately regardless of whether a reply has arrived yet.
    state = {"last_asked_date": "2026-08-27", "awaiting_reply": True}
    assert _decide(ask_cadence="daily", now=NIGHT, is_night=True, state=state) == Action.AUTO_CONTINUE


def test_daily_cadence_daytime_after_asked_but_unanswered_goes_idle():
    state = {"last_asked_date": "2026-08-27", "awaiting_reply": True}
    assert _decide(ask_cadence="daily", now=DAY, is_night=False, state=state) == Action.IDLE


def test_daily_cadence_daytime_after_answered_continues_automatically():
    state = {"last_asked_date": "2026-08-27", "awaiting_reply": False}
    assert _decide(ask_cadence="daily", now=DAY, is_night=False, state=state) == Action.AUTO_CONTINUE


def test_daily_cadence_without_night_start_never_asks():
    # No no_reserve_hours configured -> nothing to anchor the daily ask to.
    state = {}
    assert _decide(ask_cadence="daily", now=NIGHT, is_night=True, night_start=None, state=state) == Action.AUTO_CONTINUE


def test_unknown_cadence_raises():
    import pytest
    with pytest.raises(ValueError):
        _decide(ask_cadence="hourly")


# --- budget cap ---

def test_budget_cap_reached_goes_idle_during_day():
    state = {"last_asked_window_start": "2026-08-27T10:00:00+00:00", "awaiting_reply": False}
    assert _decide(state=state, budget_cap_reached=True) == Action.IDLE


# --- parse_budget_cap ---

def test_parse_budget_cap_extracts_percent():
    assert human_in_loop.parse_budget_cap("the AAPL task, cap it at 40%") == 40


def test_parse_budget_cap_absent_returns_none():
    assert human_in_loop.parse_budget_cap("just work on the AAPL task") is None


def test_parse_budget_cap_out_of_range_returns_none():
    assert human_in_loop.parse_budget_cap("cap it at 150%") is None


def test_parse_budget_cap_zero_returns_none():
    assert human_in_loop.parse_budget_cap("cap it at 0%") is None


# --- compose_ask_message ---

def test_compose_ask_message_lists_items_and_allows_free_text():
    msg = human_in_loop.compose_ask_message(["Fix the login bug", "Add retry logic"])
    assert "1. Fix the login bug" in msg
    assert "2. Add retry logic" in msg
    assert "new project" in msg.lower()
    assert "%" in msg


def test_compose_ask_message_caps_item_count():
    items = [f"item {i}" for i in range(10)]
    msg = human_in_loop.compose_ask_message(items, max_items=3)
    assert "item 2" in msg
    assert "item 3" not in msg


def test_compose_ask_message_handles_no_open_items():
    msg = human_in_loop.compose_ask_message([])
    assert "new project" in msg.lower()
