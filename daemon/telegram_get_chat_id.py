#!/usr/bin/env python3
"""Print the chat_id and sender user_id of anyone who has messaged the bot, so
you can copy the right values into TELEGRAM_ALLOWED_CHAT_ID and
TELEGRAM_OWNER_USER_ID in SQUEEZER_HOME/.env. Message your bot at least once
before running this."""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as _config  # noqa: E402


def main():
    env = _config.load_env()
    token = env.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("error: TELEGRAM_BOT_TOKEN not set in SQUEEZER_HOME/.env", file=sys.stderr)
        sys.exit(1)

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.load(resp)

    if not data.get("ok"):
        print(f"error from Telegram API: {data}", file=sys.stderr)
        sys.exit(1)

    seen = {}
    for update in data.get("result", []):
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            continue
        chat = msg["chat"]
        sender = msg.get("from") or {}
        label = sender.get("username") or sender.get("first_name") or chat.get("username") or chat.get("first_name") or "unknown"
        seen[(chat["id"], sender.get("id"))] = label

    if not seen:
        print("No messages found yet — send your bot a message on Telegram first, then re-run this.")
        return

    print("Found the following chat_id / user_id pair(s):")
    for (chat_id, user_id), label in seen.items():
        print(f"  chat_id={chat_id}  user_id={user_id}  ({label})")
    print(
        "\nFor a normal 1:1 chat these two numbers are the same value — copy it "
        "into both TELEGRAM_ALLOWED_CHAT_ID and TELEGRAM_OWNER_USER_ID in .env."
    )


if __name__ == "__main__":
    main()
