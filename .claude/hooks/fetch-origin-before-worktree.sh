#!/usr/bin/env bash
# New worktrees branch from origin/<default>, which is only as current as the
# last fetch. Refresh it first so a worktree never starts from a stale main.
set -uo pipefail

git rev-parse --git-dir >/dev/null 2>&1 || exit 0

before=$(git rev-parse --quiet --verify refs/remotes/origin/main || true)
git fetch origin --prune --quiet 2>/dev/null || exit 0
after=$(git rev-parse --quiet --verify refs/remotes/origin/main || true)

if [ -n "$after" ] && [ "$before" != "$after" ]; then
  printf '{"systemMessage":"origin/main advanced to %s; new worktrees branch from it."}\n' "${after:0:7}"
fi
