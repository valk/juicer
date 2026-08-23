# squeezer — autonomous multi-project dev orchestrator (Claude Code plugin)

A background daemon that works through TODOs across several of your local
git repos, falls back to generic maintenance work (`ROUTINE.md`) when idle,
and talks to you over Telegram — proactively surfacing summaries and
top-priority findings, escalating only genuinely in-doubt decisions, and
always keeping a configurable slice of the current 5-hour usage window free
so you can grab manual control if something looks wrong. An optional
human-in-loop mode hands control back to you at the start of every fresh
budget window (or once a day) instead of running fully unattended.

squeezer is a **Claude Code plugin** — install it once, then run
`/squeezer:setup` inside any Claude Code session. There's no tmux session and
no interactive pane to babysit: the daemon spawns a fresh headless
`claude -p --resume <session-id>` turn whenever there's work to do, resuming
the same ongoing conversation each time, and survives Claude Code's Pro-plan
5-hour rate-limit resets by simply waiting for the next window rather than
needing a wrapper to keep a live session alive through the reset.

This repo is generic on purpose: **no private project names, paths, or
secrets are committed**. Everything project-specific lives in your local
`SQUEEZER_HOME` (default `~/.config/squeezer`) — entirely separate from
wherever this plugin package itself is installed, so upgrading the plugin
never touches your registered projects, secrets, or state.

## How it works

- `daemon/daemon.py` is the only long-running process — installed as a
  launchd (macOS) or systemd `--user` (Linux) service by `/squeezer:setup`,
  so it survives reboots and crashes on its own. It long-polls Telegram,
  paces continuation turns against the token budget, and (in human-in-loop
  mode) asks what to work on next.
- Each turn is a headless `claude -p --resume <session-id>` process,
  `--add-dir`'d into every project in `config.json`, run with `cwd` set to
  `SQUEEZER_HOME` so it picks up `CLAUDE.md`/`ESCALATION_POLICY.md`/`ROUTINE.md`/
  `todos/` from there.
- The reserve is skipped (treated as 0%) during `no_reserve_hours` in
  `config.json` — hours when no one needs it free to grab manual control,
  default `02:00`–`07:00` local time. Set it to `null` to disable.
- `hooks/budget_guard.sh` sums real token usage from the session's own
  transcript and blocks further tool calls once the configured reserve is
  breached — enforced in code, not by asking the model nicely.
- The model calls the `telegram_send` MCP tool to proactively notify you or
  escalate, per `ESCALATION_POLICY.md`.

See `templates/CLAUDE.md.template` (copied to `SQUEEZER_HOME/CLAUDE.md` on
setup) for the full operating policy a running instance follows.

## Human-in-loop mode

Set `"mode": "human_in_loop"` in `config.json`, or send `/manual` to the bot
anytime (`/auto` switches back). In this mode, whenever a fresh 5-hour budget
window opens — or, with `"human_in_loop": {"ask_cadence": "daily"}`, once a
day right at `no_reserve_hours.start` — the daemon messages you the top open
TODO items and waits for a reply before doing anything else. You can reply
with a number, describe any other task, or name a brand-new project path to
register; you can also cap that session's spend (e.g. "cap it at 40%"), which
the daemon enforces as a hard stop. You're never asked or blocked during
`no_reserve_hours` — the daemon just runs fully automatically through the
night either way.

## Setup

### 1. Install the plugin

Add this repo as a plugin marketplace source and install it, then run:

```
/squeezer:setup
```

This walks you through registering your projects, setting up the Telegram
bot, and installing the background daemon as an OS service. It's idempotent
— safe to re-run any time (e.g. after adding a project).

### 2. Register your projects

`/squeezer:setup` seeds `SQUEEZER_HOME/config.json` from
`templates/config.example.json`. Replace the placeholder entries with your
own:

```json
{
  "name": "example-project-1",
  "path": "/absolute/path/to/example-project-1",
  "notes": "what this project is / any constraints the agent should know"
}
```

Each project needs git — if one doesn't have it yet, run `git init` in it
first (no remote required). This gives the agent an undo mechanism before
it's allowed to touch that project; `/squeezer:setup`'s validation step
refuses to register a project with no git history until you do this.

### 3. Create a `todos/<project>/TODO.md` for each registered project

Use `templates/TODO.md.example` as the format reference — a structured
checklist, not freeform notes. If a project already has its own informal
`TODO.md` at its repo root, leave it alone: the agent treats that as
read-only reference material, never as a task source.

### 4. Create the Telegram bot (you have to do this step yourself)

1. Message [@BotFather](https://t.me/BotFather) on Telegram, run `/newbot`,
   and save the token it gives you.
2. Send your new bot any message (e.g. "hi") so it has something to read.
3. `/squeezer:setup` fetches `getUpdates` and prints your numeric `chat_id`
   and `user_id` so only you can drive the bot. Every inbound message is
   checked against both — not just the chat, but the actual sender — so it
   stays locked to you even if the bot is ever added to a group.

## Moving to a new machine, or repointing at different projects

Nothing in this repo needs to change — it's generic plugin code. Install the
plugin on the new machine and run `/squeezer:setup` again with that
machine's real projects; `SQUEEZER_HOME` is where all machine/user-specific
state lives.

## Escalation and safety

See `templates/ESCALATION_POLICY.md.template` (copied to
`SQUEEZER_HOME/ESCALATION_POLICY.md` on setup) for what the agent handles
autonomously vs. what it escalates to you over Telegram.
