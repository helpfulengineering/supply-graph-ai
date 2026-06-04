#!/usr/bin/env python3
"""Extract one version section from CHANGELOG.md for GitHub Release notes.

Usage:
    python scripts/extract_changelog_section.py 0.8.0 > /tmp/release-notes.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CHANGELOG = _ROOT / "CHANGELOG.md"


def extract(version: str) -> str:
    if not _CHANGELOG.is_file():
        raise FileNotFoundError(f"Missing {_CHANGELOG}")
    prefix = f"## [{version}]"
    lines = _CHANGELOG.read_text(encoding="utf-8").splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith(prefix):
            start = i + 1
            break
    if start is None:
        raise ValueError(f"No section starting with {prefix!r} in {_CHANGELOG}")

    out: list[str] = []
    for line in lines[start:]:
        if line.startswith("## [") or line.startswith("## [Unreleased]"):
            break
        if line.startswith("[") and line.endswith("]:") and "://" in line:
            continue
        out.append(line)
    body = "\n".join(out).strip()
    if not body:
        raise ValueError(f"Empty changelog section for {version}")
    return body


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract CHANGELOG section for a version"
    )
    parser.add_argument("version", help="Semver without v prefix (e.g. 0.8.0)")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write notes to file (default: stdout)",
    )
    args = parser.parse_args()
    text = extract(args.version.strip())
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
