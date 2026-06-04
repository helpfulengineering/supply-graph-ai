#!/usr/bin/env python3
"""Bump the package version in pyproject.toml (single source of truth).

Usage:
    python scripts/bump_version.py 0.8.0
    uv run python scripts/bump_version.py 0.9.0

After bumping, run:
    uv lock
    uv sync --extra dev
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT = _ROOT / "pyproject.toml"
_VERSION_RE = re.compile(r"^version\s*=\s*\"[^\"]+\"", re.MULTILINE)
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bump version in pyproject.toml")
    parser.add_argument(
        "version",
        help="New semver version (e.g. 0.8.0)",
    )
    args = parser.parse_args()
    new_version = args.version.strip()
    if not _SEMVER_RE.match(new_version):
        print(
            f"Invalid semver: {new_version!r} (expected MAJOR.MINOR.PATCH)",
            file=sys.stderr,
        )
        return 1

    text = _PYPROJECT.read_text(encoding="utf-8")
    if not _VERSION_RE.search(text):
        print(f"No version field found in {_PYPROJECT}", file=sys.stderr)
        return 1

    old_match = _VERSION_RE.search(text)
    old_line = old_match.group(0) if old_match else "?"
    new_text = _VERSION_RE.sub(f'version = "{new_version}"', text, count=1)
    _PYPROJECT.write_text(new_text, encoding="utf-8")
    print(f'Updated {_PYPROJECT.name}: {old_line} -> version = "{new_version}"')
    print("Next: uv lock && uv sync --extra dev")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
