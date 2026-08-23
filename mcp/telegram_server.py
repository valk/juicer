#!/usr/bin/env python3
"""MCP server exposing telegram_send only — for proactive notifications and
escalations the model decides to send (per ESCALATION_POLICY.md). This is
deliberately NOT the pause/budget/continuation enforcement path; those are
hook- and orchestrator-enforced so they work whether or not the model calls
a tool. See CLAUDE.md.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "daemon"))
import telegram_lib  # noqa: E402

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("squeezer-telegram")


@mcp.tool()
def telegram_send(message: str) -> str:
    """Send a message to the human's Telegram (proactive summary, top-priority
    finding, or an escalation per ESCALATION_POLICY.md). One-way — for a
    genuine escalation, phrase the specific decision needed and then stop
    working on that item until a reply arrives (it will appear in this
    session tagged [Telegram/User]: ...)."""
    telegram_lib.send_message(message)
    return "sent"


if __name__ == "__main__":
    mcp.run()
