#!/usr/bin/env bash
# PreToolUse hook: blocks tool calls once the configured token reserve is
# breached for the current window. Reads real usage from the session's own
# transcript (not a heuristic) via daemon/usage_lib.py — which itself reads
# and writes SQUEEZER_HOME (the per-install control directory), never this
# hook's own location, so this resolves correctly whether squeezer is
# installed as a plugin (CLAUDE_PLUGIN_ROOT set by Claude Code) or run
# directly from a checkout of this repo for squeezer's own development
# (falls back to this file's own repo layout).
set -euo pipefail
DIR="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
exec python3 "$DIR/daemon/usage_lib.py" check
