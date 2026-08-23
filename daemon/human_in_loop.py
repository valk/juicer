#!/usr/bin/env python3
"""Decision engine for squeezer's human-in-loop mode (see CLAUDE.md's
"Human-in-loop mode" section). Pure functions only — no I/O, no subprocess,
no Telegram. daemon.py owns state persistence and does the actual
asking/spawning; this module just decides what to do on a given tick, so the
scheduling logic is unit-testable without mocking a clock-driven loop.
"""
import re
from datetime import datetime, time
from enum import Enum

_PERCENT_RE = re.compile(r"(\d{1,3})\s*%")


class Action(str, Enum):
    AUTO_CONTINUE = "auto_continue"  # proceed exactly like fully-automatic mode
    SEND_ASK = "send_ask"            # send the "what next" prompt now
    IDLE = "idle"                    # do nothing this tick


def _is_ask_due(ask_cadence: str, now: datetime, window_start_ts: str, state: dict, night_start: time | None) -> bool:
    if ask_cadence == "every_window_reset":
        return state.get("last_asked_window_start") != window_start_ts
    if ask_cadence == "daily":
        if night_start is None:
            return False  # nothing to anchor the daily ask to without a configured night start
        today = now.date().isoformat()
        return now.time() >= night_start and state.get("last_asked_date") != today
    raise ValueError(f"unknown ask_cadence: {ask_cadence!r}")


def decide_action(
    *,
    mode: str,
    ask_cadence: str,
    now: datetime,
    is_night: bool,
    night_start: time | None,
    window_start_ts: str,
    state: dict,
    budget_cap_reached: bool,
) -> Action:
    """The single decision point the daemon consults every tick. `mode` ==
    "auto" always short-circuits to AUTO_CONTINUE — everything below only
    applies once mode == "human_in_loop"."""
    if mode != "human_in_loop":
        return Action.AUTO_CONTINUE

    due = _is_ask_due(ask_cadence, now, window_start_ts, state, night_start)
    # every_window_reset asks are suppressed overnight (never disturb sleep);
    # the daily ask's own trigger IS the night boundary, so it's exempt from
    # that suppression — that's what makes it fire in the first place.
    if due and not (is_night and ask_cadence == "every_window_reset"):
        return Action.SEND_ASK

    if is_night:
        # Night behavior is always "auto": work straight through, unasked
        # and unblocked, regardless of a pending question or a hit cap.
        return Action.AUTO_CONTINUE

    if state.get("awaiting_reply") or budget_cap_reached:
        return Action.IDLE

    return Action.AUTO_CONTINUE


def parse_budget_cap(reply_text: str) -> int | None:
    """Pull a token-budget percentage out of a human reply, e.g. "the AAPL
    task, cap it at 40%" -> 40. None if absent or out of [1, 100]."""
    match = _PERCENT_RE.search(reply_text)
    if not match:
        return None
    value = int(match.group(1))
    return value if 1 <= value <= 100 else None


def compose_ask_message(todo_items: list[str], max_items: int = 5) -> str:
    """The Telegram "what next" prompt: top open TODO items plus free text
    for anything else, including registering a new project."""
    lines = ["Fresh budget window — what would you like me to work on?", ""]
    if todo_items:
        for i, item in enumerate(todo_items[:max_items], 1):
            lines.append(f"{i}. {item}")
        lines.append("")
    lines.append(
        "Reply with a number, describe any other task, or name a new project "
        "path to register and start on. You can also cap this session's "
        "spend, e.g. \"#2, cap it at 40%\"."
    )
    return "\n".join(lines)
