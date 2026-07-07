#!/usr/bin/env python3
"""Bump the OHM version everywhere it is claimed, from one source of truth.

`pyproject.toml` is the canonical version. A small registry (`_SITES`) lists the
*other* places that state the **current** release as literal text — these are the
drift-prone spots. One command rewrites them all in lockstep; `--check` verifies
they still match (a staleness gate for `make ready`).

Only "current release" claims belong in the registry (README badge, quickstart
docker tags). Historical facts (CHANGELOG, "added in 0.8.x") and illustrative
examples ("e.g. v0.8.0") must NOT be listed — they are correctly pinned to a
specific version and should never move. Docker examples in the docs float on the
`:0.8` major.minor tag on purpose, so they never drift and are not registered.

Usage:
    python scripts/bump_version.py 0.9.0     # bump pyproject + registry
    python scripts/bump_version.py --check    # verify registry == pyproject

After a bump, run:
    uv lock && uv sync --extra dev
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT = _ROOT / "pyproject.toml"
_PYPROJECT_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass(frozen=True)
class Site:
    """A file location that states the current release as literal text.

    ``pattern`` must contain a named group ``v`` capturing a full semver; only
    that group is rewritten, so surrounding text is preserved verbatim.
    """

    relpath: str
    pattern: re.Pattern[str]
    label: str


# The registry. Keep this list minimal — every entry is a promise to keep that
# spot exactly equal to pyproject. Prefer floating tags / pointers over adding
# rows here (see module docstring).
_SITES: list[Site] = [
    Site(
        "README.md",
        re.compile(r"\*\*Current release:\*\*\s+`(?P<v>\d+\.\d+\.\d+)`"),
        "current-release line",
    ),
    Site(
        "README.md",
        re.compile(r"openhardwaremanager:(?P<v>\d+\.\d+\.\d+)"),
        "quickstart docker tag",
    ),
]


def read_pyproject_version() -> str:
    match = _PYPROJECT_VERSION_RE.search(_PYPROJECT.read_text(encoding="utf-8"))
    if not match:
        raise RuntimeError(f"No version field found in {_PYPROJECT}")
    return match.group(1)


def _swap_version(match: re.Match[str], new_version: str) -> str:
    """Return the full match text with only its ``v`` group set to new_version."""
    whole = match.group(0)
    start = match.start("v") - match.start()
    end = match.end("v") - match.start()
    return whole[:start] + new_version + whole[end:]


def _scan_site(site: Site) -> tuple[str, list[str]]:
    """Return (file text, list of versions found at this site)."""
    text = (_ROOT / site.relpath).read_text(encoding="utf-8")
    found = [m.group("v") for m in site.pattern.finditer(text)]
    return text, found


def check(target: str) -> int:
    """Fail if any registered site disagrees with `target` (pyproject version)."""
    problems: list[str] = []
    for site in _SITES:
        _, found = _scan_site(site)
        if not found:
            problems.append(
                f"{site.relpath}: pattern for {site.label!r} matched nothing "
                f"(file changed? update _SITES in scripts/bump_version.py)"
            )
            continue
        stale = sorted({v for v in found if v != target})
        if stale:
            problems.append(
                f"{site.relpath}: {site.label} is {', '.join(stale)}, "
                f"expected {target}"
            )
    if problems:
        print("Version drift detected (canonical = pyproject.toml):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print(
            "Fix: run `python scripts/bump_version.py "
            f"{target}` to resync, then commit.",
            file=sys.stderr,
        )
        return 1
    print(f"OK: {len(_SITES)} version site(s) match pyproject {target}")
    return 0


def bump(new_version: str) -> int:
    if not _SEMVER_RE.match(new_version):
        print(
            f"Invalid semver: {new_version!r} (expected MAJOR.MINOR.PATCH)",
            file=sys.stderr,
        )
        return 1

    text = _PYPROJECT.read_text(encoding="utf-8")
    if not _PYPROJECT_VERSION_RE.search(text):
        print(f"No version field found in {_PYPROJECT}", file=sys.stderr)
        return 1
    old = read_pyproject_version()
    _PYPROJECT.write_text(
        _PYPROJECT_VERSION_RE.sub(f'version = "{new_version}"', text, count=1),
        encoding="utf-8",
    )
    print(f"pyproject.toml: {old} -> {new_version}")

    for site in _SITES:
        original, found = _scan_site(site)
        if not found:
            print(
                f"WARNING: {site.relpath}: pattern for {site.label!r} matched "
                f"nothing; nothing updated there.",
                file=sys.stderr,
            )
            continue
        updated = site.pattern.sub(lambda m: _swap_version(m, new_version), original)
        if updated != original:
            (_ROOT / site.relpath).write_text(updated, encoding="utf-8")
            print(f"{site.relpath}: {site.label} -> {new_version}")

    print("Next: uv lock && uv sync --extra dev")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bump the OHM version across pyproject and the registry."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "version",
        nargs="?",
        help="New semver version (e.g. 0.9.0)",
    )
    group.add_argument(
        "--check",
        action="store_true",
        help="Verify registered sites match pyproject; do not write.",
    )
    args = parser.parse_args()

    if args.check:
        return check(read_pyproject_version())
    return bump(args.version.strip())


if __name__ == "__main__":
    raise SystemExit(main())
