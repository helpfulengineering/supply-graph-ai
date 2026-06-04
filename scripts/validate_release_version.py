#!/usr/bin/env python3
"""Validate git release tag against pyproject.toml version.

Usage:
    uv run python scripts/validate_release_version.py --tag v0.8.0
    uv run python scripts/validate_release_version.py  # pyproject only (workflow_dispatch)

Writes GitHub Actions outputs when GITHUB_OUTPUT is set:
    version, major_minor
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT = _ROOT / "pyproject.toml"
_TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)$")
_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def read_pyproject_version() -> str:
    text = _PYPROJECT.read_text(encoding="utf-8")
    match = _VERSION_RE.search(text)
    if not match:
        raise RuntimeError(f"No version field in {_PYPROJECT}")
    return match.group(1)


def major_minor(version: str) -> str:
    parts = version.split(".")
    return f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else version


def write_github_output(version: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    mm = major_minor(version)
    with open(output_path, "a", encoding="utf-8") as fh:
        fh.write(f"version={version}\n")
        fh.write(f"major_minor={mm}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate release tag vs pyproject version"
    )
    parser.add_argument(
        "--tag",
        help="Git tag (e.g. v0.8.0). Omit for workflow_dispatch (pyproject version only).",
    )
    args = parser.parse_args()

    project_version = read_pyproject_version()
    if not _SEMVER_RE.match(project_version):
        print(f"Invalid pyproject version: {project_version!r}", file=sys.stderr)
        return 1

    if args.tag:
        match = _TAG_RE.match(args.tag.strip())
        if not match:
            print(
                f"Invalid tag {args.tag!r}: expected format vMAJOR.MINOR.PATCH (e.g. v0.8.0)",
                file=sys.stderr,
            )
            return 1
        tag_version = match.group(1)
        if tag_version != project_version:
            print(
                f"Version mismatch: git tag {args.tag!r} -> {tag_version!r}, "
                f"pyproject.toml has {project_version!r}",
                file=sys.stderr,
            )
            return 1
        version = tag_version
        print(f"OK: tag {args.tag} matches pyproject version {version}")
    else:
        version = project_version
        print(f"OK: pyproject version {version} (no tag supplied)")

    write_github_output(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
