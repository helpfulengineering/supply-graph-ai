#!/usr/bin/env bash
# PreToolUse(Bash) guard: refuse `git commit` while a hook-generated file is
# modified-but-unstaged.
#
# pre-commit stashes unstaged changes to a patch OUTSIDE git, runs the hooks,
# then reapplies. The `update repository map` hook rewrites .repo-map.md — so if
# that file is also in the stash, the reapply conflicts, pre-commit rolls back,
# and every unstaged change in that patch silently disappears from the working
# tree. Nothing lands in `git stash`, so it does not look like data loss; it
# looks like a hook error.
#
# This bit once: a commit with .repo-map.md unstaged stranded 7 unrelated
# storage/ files. They were only recoverable by hand from
# ~/.cache/pre-commit/patch*. See ~/.claude/lessons/ledger.md.
#
# Fix is simply to stage the generated file alongside the commit.
set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c \
  "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" \
  2>/dev/null || true)

# Only guard real commits, not `git log`, `git commit --help`, etc.
if ! printf '%s' "$cmd" | grep -qE '(^|[&|;[:space:]])git[[:space:]]+([^&|;]*[[:space:]])?commit([[:space:]]|$)'; then
  exit 0
fi
if printf '%s' "$cmd" | grep -qE '(^|[[:space:]])(-h|--help)([[:space:]]|$)'; then
  exit 0
fi
# --no-verify skips pre-commit entirely, so the stash race cannot happen.
if printf '%s' "$cmd" | grep -qE '(^|[[:space:]])(-n|--no-verify)([[:space:]]|$)'; then
  exit 0
fi

# Files rewritten by pre-commit hooks in this repo. Add to this list if a new
# generating hook is introduced.
GENERATED_FILES=(".repo-map.md")

unstaged=""
for f in "${GENERATED_FILES[@]}"; do
  # Tracked, modified, and NOT staged -> it is in the stash pre-commit will
  # fail to reapply.
  if git diff --name-only -- "$f" 2>/dev/null | grep -q .; then
    unstaged="${unstaged}${f} "
  fi
done

if [ -n "$unstaged" ]; then
  echo "Blocked: ${unstaged}is modified but not staged, and a pre-commit hook regenerates it." >&2
  echo "pre-commit stashes unstaged changes outside git; when a hook rewrites a file in that stash the reapply fails, and ALL unstaged changes are silently dropped from the working tree (recoverable only from ~/.cache/pre-commit/patch*)." >&2
  echo "Fix: stage it with the rest of the commit -> git add ${unstaged}" >&2
  exit 2
fi

exit 0
