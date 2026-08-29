#!/usr/bin/env bash
# PreToolUse(Bash) guard: refuse a frontend build while a server is serving the
# build directory it is about to overwrite.
#
# `next build` rewrites .next in place. A `next dev` or `next start` already
# serving from that directory does not reload cleanly when it is replaced mid-
# flight; it keeps answering, but with a mixture of the old manifest and the new
# chunks. Playwright then makes it worse: `reuseExistingServer: !CI` means the
# next test run ATTACHES to that corrupted server instead of starting a clean
# one, so the failures look like they belong to the code under test.
#
# This bit once, while verifying a fix: 18 specs "failed" across every run and
# the change looked like a regression. The same suite against a freshly started
# server passed 21/21. The code had never been wrong.
#
# Fix is to stop the server first, or build somewhere it is not serving from.
set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c \
  "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" \
  2>/dev/null || true)

# Only guard commands that actually rebuild the frontend.
if ! printf '%s' "$cmd" | grep -qE '(npm|pnpm|yarn)[[:space:]]+run[[:space:]]+build|next[[:space:]]+build'; then
  exit 0
fi

# The port the app is served on. harness.config.json is the source of truth;
# fall back to the Next/Vite default this repo uses.
PORT=$(python3 -c "
import json,re,sys
try:
    url = json.load(open('${CLAUDE_PROJECT_DIR:-.}/frontend/harness.config.json'))['appUrl']
    m = re.search(r':(\d+)', url)
    print(m.group(1) if m else 5173)
except Exception:
    print(5173)
" 2>/dev/null || echo 5173)

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  holder=$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -Fc 2>/dev/null | sed -n 's/^c//p' | head -1)
  echo "Blocked: a server (${holder:-unknown}) is listening on :$PORT, and this command rewrites the build directory it is serving from." >&2
  echo "Overwriting .next under a running server leaves it answering with a mix of old and new output. Playwright's reuseExistingServer then attaches the NEXT test run to that server, and the failures read as though they belong to your change." >&2
  echo "Fix: stop it first -> lsof -ti:$PORT | xargs kill -9   (then build, then let Playwright start a clean one)" >&2
  exit 2
fi

exit 0
