#!/usr/bin/env python3
"""Changelog fragments: so two PRs never edit the same line of CHANGELOG.md.

Every PR that merged a real `[Unreleased]` bullet directly into CHANGELOG.md
conflicted with the next one that did the same, at the same lines, every
time — the fix was always "strip the hunk, land one consolidated PR at the
end", done by hand, over and over. This makes that mechanical.

A PR that wants a changelog entry adds a small file to `changelog.d/`,
instead of editing CHANGELOG.md:

    changelog.d/<issue-or-pr-number>.<category>.md

`category` is one of added / changed / deprecated / removed / fixed /
security (Keep a Changelog's own sections). The file's content is exactly the
bullet body, without the leading "- " — this script adds that when it renders.
Two PRs adding two different files never conflict; that is the entire point.

CHANGELOG.md's `[Unreleased]` section is not hand-edited between
consolidations — `check()` fails if it changed since the hash recorded in
`changelog.d/.unreleased.sha256`, the same "generator plus a drift check"
shape as `bump_version.py --check`. Folding fragments in is `--consolidate`,
a deliberate, standalone step (typically right before a release), not
something any feature PR's `make ready` run does — if it were, two PRs
consolidating independently would go right back to conflicting on the same
lines.

Usage:
    python scripts/render_changelog.py --check         # make ready gate
    python scripts/render_changelog.py --consolidate    # fold fragments in
    python scripts/render_changelog.py --refreeze        # re-baseline after
                                                           # a deliberate hand
                                                           # edit (e.g. cutting
                                                           # a release section)
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[1]
_CHANGELOG = _ROOT / "CHANGELOG.md"
_FRAGMENTS_DIR = _ROOT / "changelog.d"
_HASH_FILE = _FRAGMENTS_DIR / ".unreleased.sha256"
_UNRELEASED_HEADING = "## [Unreleased]"

# Keep a Changelog's own category order — not the order today's hand-written
# section happens to use, since that grew organically and this is the order
# new categories get inserted in from here on.
_CATEGORY_ORDER = [
    "added",
    "changed",
    "deprecated",
    "removed",
    "fixed",
    "security",
]
_CATEGORY_HEADING = {c: c[0].upper() + c[1:] for c in _CATEGORY_ORDER}
_FRAGMENT_RE = re.compile(
    r"^(?P<number>\d+)\.(?P<category>[a-z]+)(?:\.[a-z0-9-]+)?\.md$"
)


class ChangelogError(RuntimeError):
    """A fragment or CHANGELOG.md itself is not in the expected shape."""


@dataclass(frozen=True)
class Fragment:
    path: Path
    number: int
    category: str

    @property
    def body(self) -> str:
        return self.path.read_text(encoding="utf-8").strip()


def _fragments() -> List[Fragment]:
    if not _FRAGMENTS_DIR.is_dir():
        return []
    found = []
    for path in sorted(_FRAGMENTS_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        match = _FRAGMENT_RE.match(path.name)
        if not match:
            raise ChangelogError(
                f"{path.relative_to(_ROOT)}: filename must be "
                "<issue-number>.<category>.md (optionally "
                "<issue-number>.<category>.<slug>.md), category one of "
                f"{', '.join(_CATEGORY_ORDER)}"
            )
        category = match.group("category")
        if category not in _CATEGORY_ORDER:
            raise ChangelogError(
                f"{path.relative_to(_ROOT)}: unknown category {category!r}, "
                f"expected one of {', '.join(_CATEGORY_ORDER)}"
            )
        if not path.read_text(encoding="utf-8").strip():
            raise ChangelogError(f"{path.relative_to(_ROOT)}: empty fragment")
        found.append(
            Fragment(path=path, number=int(match.group("number")), category=category)
        )
    return found


def _read_changelog() -> List[str]:
    if not _CHANGELOG.is_file():
        raise ChangelogError(f"Missing {_CHANGELOG}")
    return _CHANGELOG.read_text(encoding="utf-8").splitlines()


def _unreleased_span(lines: List[str]) -> tuple[int, int]:
    """(start, end) line indices of the Unreleased section's *body* — after
    its own heading, up to (not including) the next `## [` heading."""
    start = None
    for i, line in enumerate(lines):
        if line.strip() == _UNRELEASED_HEADING:
            start = i + 1
            break
    if start is None:
        raise ChangelogError(f"No {_UNRELEASED_HEADING!r} heading in {_CHANGELOG}")
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("## ["):
            end = i
            break
    return start, end


def _unreleased_body(lines: List[str]) -> str:
    start, end = _unreleased_span(lines)
    return "\n".join(lines[start:end]).strip("\n")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _recorded_hash() -> Optional[str]:
    if not _HASH_FILE.is_file():
        return None
    return _HASH_FILE.read_text(encoding="utf-8").strip()


def check() -> int:
    problems: List[str] = []

    try:
        fragments = _fragments()
    except ChangelogError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    lines = _read_changelog()
    current = _hash(_unreleased_body(lines))
    recorded = _recorded_hash()
    if recorded is None:
        problems.append(
            f"{_HASH_FILE.relative_to(_ROOT)} is missing. Run "
            "`python scripts/render_changelog.py --refreeze` once to "
            "establish the baseline."
        )
    elif current != recorded:
        problems.append(
            "CHANGELOG.md's [Unreleased] section was edited directly "
            f"(hash {current[:12]}… != recorded {recorded[:12]}…).\n"
            "    Add a changelog.d/<issue-number>.<category>.md fragment "
            "instead — see changelog.d/README.md.\n"
            "    If this edit was a deliberate consolidation, run "
            "`python scripts/render_changelog.py --refreeze` to re-baseline."
        )

    if problems:
        print("FAIL:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(
        f"OK: [Unreleased] matches its recorded hash; "
        f"{len(fragments)} pending fragment(s)."
    )
    return 0


def _bullet_lines(entry: Fragment) -> List[str]:
    """The fragment's body as a bullet: "- " on the first line; a
    continuation line that is not already indented gets the standard 2
    spaces so an author who forgets still gets a bullet that renders
    correctly, rather than a line that reads as a new top-level paragraph."""
    body_lines = entry.body.splitlines()
    out = [f"- {body_lines[0]}"]
    for line in body_lines[1:]:
        out.append(line if (not line or line.startswith(" ")) else f"  {line}")
    return out


@dataclass
class _Section:
    heading: Optional[str]  # None only for a (normally empty) preamble
    lines: List[str]


def _split_sections(body_lines: List[str]) -> List[_Section]:
    sections = [_Section(heading=None, lines=[])]
    for line in body_lines:
        if line.startswith("### "):
            sections.append(_Section(heading=line[4:].strip(), lines=[]))
        else:
            sections[-1].lines.append(line)
    return sections


def _render_section(section: _Section) -> str:
    body = "\n".join(section.lines).strip("\n")
    if section.heading is None:
        return body
    return f"### {section.heading}" + (f"\n\n{body}" if body else "")


def consolidate() -> int:
    fragments = _fragments()
    if not fragments:
        print("Nothing to consolidate: changelog.d/ has no fragments.")
        return 0

    lines = _read_changelog()
    start, end = _unreleased_span(lines)
    sections = _split_sections(lines[start:end])

    by_category: Dict[str, List[Fragment]] = {}
    for f in fragments:
        by_category.setdefault(f.category, []).append(f)

    for category in _CATEGORY_ORDER:
        entries = by_category.get(category)
        if not entries:
            continue
        heading = _CATEGORY_HEADING[category]
        new_lines = [
            line
            for entry in sorted(entries, key=lambda f: f.number)
            for line in _bullet_lines(entry)
        ]
        existing = next((s for s in sections if s.heading == heading), None)
        if existing is not None:
            existing.lines = [ln for ln in existing.lines if ln != ""] + new_lines
        else:
            sections.append(_Section(heading=heading, lines=new_lines))

    # The heading-less preamble is never real content in this file — just
    # the blank line between "## [Unreleased]" and the first "### " — so it
    # is dropped here and re-added explicitly below, rather than trusted to
    # survive `.strip("\n")` (it doesn't: a leading blank joined onto real
    # text is exactly what that strips).
    rendered_sections = [_render_section(s) for s in sections if s.heading]
    new_unreleased = "\n\n".join(rendered_sections).strip("\n")

    new_lines = lines[:start] + [""] + new_unreleased.splitlines() + [""] + lines[end:]
    _CHANGELOG.write_text("\n".join(new_lines).rstrip("\n") + "\n", encoding="utf-8")

    for f in fragments:
        f.path.unlink()

    _HASH_FILE.write_text(_hash(new_unreleased) + "\n", encoding="utf-8")
    print(
        f"Consolidated {len(fragments)} fragment(s) into CHANGELOG.md "
        f"and removed them from {_FRAGMENTS_DIR.relative_to(_ROOT)}."
    )
    return 0


def refreeze() -> int:
    lines = _read_changelog()
    body = _unreleased_body(lines)
    _FRAGMENTS_DIR.mkdir(exist_ok=True)
    _HASH_FILE.write_text(_hash(body) + "\n", encoding="utf-8")
    print(f"Recorded {_HASH_FILE.relative_to(_ROOT)}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="make ready gate")
    group.add_argument(
        "--consolidate", action="store_true", help="fold changelog.d/ fragments in"
    )
    group.add_argument(
        "--refreeze",
        action="store_true",
        help="re-baseline the recorded hash after a deliberate hand edit",
    )
    args = parser.parse_args()

    try:
        if args.check:
            return check()
        if args.consolidate:
            return consolidate()
        return refreeze()
    except ChangelogError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
