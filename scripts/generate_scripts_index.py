#!/usr/bin/env python3
"""Generate scripts/README.md from scripts/registry.toml.

The registry (`scripts/registry.toml`) is the source of truth for what lives in
scripts/ and what each tool is for. This renders it into a human/agent-readable
index grouped by category, and (with --check) enforces two invariants so the
directory can't silently re-crowd:

  1. Completeness — every scripts/*.py and *.sh has a registry entry, and every
     entry names a script that exists (mirrors tests/parity/manifest.py).
  2. Freshness — scripts/README.md matches what the registry would render.

Usage:
    uv run python scripts/generate_scripts_index.py            # write README.md
    uv run python scripts/generate_scripts_index.py --check     # verify only
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
_REGISTRY = _SCRIPTS / "registry.toml"
_README = _SCRIPTS / "README.md"

# Fixed category order for a stable, meaningful index.
_CATEGORY_ORDER = [
    ("release", "Release & versioning"),
    ("generate", "Code / doc generation"),
    ("verify", "Verification & validation gates"),
    ("data", "Synthetic data & seeding"),
    ("storage", "Storage operations"),
    ("deploy", "Deployment pathways"),
    ("federation", "Federation testing"),
    ("eval", "LLM & matching evaluation"),
]
_KNOWN_CATEGORIES = {c for c, _ in _CATEGORY_ORDER}


def discover_scripts() -> set[str]:
    """Filenames (without extension) of the actual executables in scripts/."""
    names: set[str] = set()
    for f in _SCRIPTS.iterdir():
        if f.suffix in {".py", ".sh"} and f.name != Path(__file__).name:
            names.add(f.stem)
    # The generator registers itself too.
    names.add(Path(__file__).stem)
    return names


def load_registry() -> dict[str, dict]:
    data = tomllib.loads(_REGISTRY.read_text(encoding="utf-8"))
    return data.get("scripts", {})


def check_completeness(entries: dict[str, dict]) -> list[str]:
    problems: list[str] = []
    registered = set(entries)
    actual = discover_scripts()

    for name in sorted(actual - registered):
        problems.append(f"scripts/{name}.* exists but has no registry.toml entry")
    for name in sorted(registered - actual):
        problems.append(f"registry.toml lists '{name}' but no such script exists")

    for name, meta in sorted(entries.items()):
        cat = meta.get("category")
        if cat not in _KNOWN_CATEGORIES:
            problems.append(
                f"'{name}': category {cat!r} is not one of {sorted(_KNOWN_CATEGORIES)}"
            )
        for field in ("summary", "run"):
            if not meta.get(field):
                problems.append(f"'{name}': missing required field '{field}'")
    return problems


def render(entries: dict[str, dict]) -> str:
    lines = [
        "<!-- Generated from scripts/registry.toml by scripts/generate_scripts_index.py.",
        "     Do not edit by hand — edit the registry and run `make scripts` (or scripts-check). -->",
        "",
        "# Scripts",
        "",
        "Developer and ops tooling for OHM. Source of truth is "
        "[`registry.toml`](registry.toml); this index is generated from it. Every "
        "script here is registered — `make scripts-check` fails otherwise.",
        "",
        "A ✎ marks a script that **writes** files / storage / remote state; the "
        "rest are read-only (safe to run to inspect state).",
        "",
    ]
    by_cat: dict[str, list[tuple[str, dict]]] = {}
    for name, meta in entries.items():
        by_cat.setdefault(meta.get("category", "?"), []).append((name, meta))

    for cat, heading in _CATEGORY_ORDER:
        items = sorted(by_cat.get(cat, []))
        if not items:
            continue
        lines.append(f"## {heading}")
        lines.append("")
        lines.append("| Script | What it does | Run |")
        lines.append("| --- | --- | --- |")
        for name, meta in items:
            mark = " ✎" if meta.get("mutates") else ""
            summary = meta.get("summary", "").replace("|", "\\|")
            run = f"`{meta.get('run', '').replace('|', '\\|')}`"
            lines.append(f"| `{name}`{mark} | {summary} | {run} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate scripts/README.md from registry.toml"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify registry completeness and README freshness; do not write.",
    )
    args = parser.parse_args()

    entries = load_registry()
    problems = check_completeness(entries)
    rendered = render(entries)

    if args.check:
        if problems:
            print("Script registry problems:", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            print(
                "Fix scripts/registry.toml, then run `make scripts`.", file=sys.stderr
            )
            return 1
        current = _README.read_text(encoding="utf-8") if _README.is_file() else ""
        if current != rendered:
            print(
                "scripts/README.md is out of date with registry.toml. "
                "Run `make scripts` and commit.",
                file=sys.stderr,
            )
            return 1
        print(f"OK: {len(entries)} scripts registered; README.md current.")
        return 0

    if problems:
        # Refuse to render a README from an inconsistent registry.
        print("Refusing to generate — fix these first:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    _README.write_text(rendered, encoding="utf-8")
    print(f"Wrote {_README.relative_to(_SCRIPTS.parent)} ({len(entries)} scripts).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
