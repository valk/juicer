# Developing squeezer itself

This is squeezer's own plugin source repo — `bin/`, `daemon/`, `hooks/`,
`agents/`, `commands/`, `mcp/`, `.claude-plugin/`, `templates/`. It is
**not** where any live orchestration data lives: registered projects, TODOs,
worklog, and secrets all live in `SQUEEZER_HOME` (default
`~/.config/squeezer`), created and populated by the `/squeezer:setup` command
from this repo's `templates/`. See `README.md` for the install/setup flow and
`templates/CLAUDE.md.template` for the operating policy an actual running
instance follows.

Every new feature added to squeezer gets minimal tests under `tests/`
(pytest) covering its behavior — see `tests/test_human_in_loop.py` and
`tests/test_config.py` for the pattern of loading a `daemon/*.py` module via
`importlib` and pointing it at a scratch `SQUEEZER_HOME` (via
`monkeypatch.setenv("SQUEEZER_HOME", ...)`) rather than the real one. Run
`python3 -m pytest tests/` before considering such a task done.

## This repo is public — never use real names

`squeezer` is a public GitHub repo (`valk/squeezer`). Anything committed here
is visible to anyone. Since real project names/paths, secrets, and the
user's own TODOs/worklog all live in `SQUEEZER_HOME` — entirely outside this
repo — they structurally can't end up in a tracked file here as long as you
don't hardcode them into this repo's own code, docs, or tests. Keep it that
way: no real name belongs in a tracked file (use `user`/`admin` instead, as
in the `[Telegram/User]` tag), no real registered project's name, path, or
business details (use placeholders like `example-project`, `acme`,
`/absolute/path/to/example-project` — `templates/config.example.json` and
`templates/TODO.md.example` are the templates, keep them placeholder-only),
and no local machine username baked into an absolute path (e.g.
`/Users/<name>/...`). Same goes for API keys, tokens, or other secrets —
`templates/env.example` already enforces this pattern (real values only ever
go in the gitignored, SQUEEZER_HOME-local `.env`); follow it for anything
new. Before committing changes to this repo, check `git status`/`git diff`
for any of the above — if in doubt, treat it as private and keep it out.

Any leftover `projects.json`, `.env`, `todos/`, or `state/` you find at this
repo's root are gitignored artifacts from squeezer's pre-plugin architecture
(when this repo doubled as its own `SQUEEZER_HOME`) — read-only history, not
something new code should read from or write to.
