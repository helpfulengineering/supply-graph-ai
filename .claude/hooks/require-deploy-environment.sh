#!/usr/bin/env bash
# PreToolUse(Bash) guard: refuse to run deploy_azure.py without an explicit
# --environment. Importing src.config runs load_dotenv(), so the deploy target
# would otherwise be inferred from a developer's local .env — which once applied
# development.toml (STORAGE_PROVIDER=local) to the PRODUCTION container app.
# The deploy target must always be explicit. See ~/.claude/lessons/ledger.md.
set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c \
  "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" \
  2>/dev/null || true)

# Only guard actual invocations (python3/uv run … deploy_azure.py), not
# cat/grep/reads of the file.
if printf '%s' "$cmd" | grep -qE '(python[0-9]*|uv run)[^&|;]*deploy_azure\.py'; then
  # Allow help/inspection.
  if printf '%s' "$cmd" | grep -qE '(^|[[:space:]])(-h|--help)([[:space:]]|$)'; then
    exit 0
  fi
  # Require an explicit deploy target.
  if ! printf '%s' "$cmd" | grep -qE '(^|[[:space:]])--environment([[:space:]]|=)'; then
    echo "Blocked: deploy_azure.py invoked without --environment. The deploy target must be explicit — importing src.config runs load_dotenv(), so a local .env (ENVIRONMENT=development) can silently redirect the deploy and mis-point prod. Re-run with an explicit target, e.g. --environment production." >&2
    exit 2
  fi
fi

exit 0
