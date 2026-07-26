#!/usr/bin/env python3
"""Stage the public documentation site for building.

Copies ``docs-site/docs/`` (authored markdown) into ``docs-site/.build/``
(generated), injecting build-status badges and writing the generated
"what's built" page. Whatever static site generator runs afterwards points at
the staging directory, never at the source.

Why a staging step instead of a MkDocs hook
-------------------------------------------
Status must come from exactly one source of truth — ``SITE_DOCS`` in
``tests/parity/manifest.py`` — with nothing duplicated in git that could drift.
A MkDocs hook achieves that, but welds the docs pipeline to MkDocs at precisely
the moment MkDocs 2.0 is dropping its plugin system and saying nothing about
hooks. Staging keeps the single-source property *and* leaves the generator
swappable: the gate (``tests/parity/test_docs_status.py``) is pure Python over
markdown frontmatter and never imports MkDocs either.

A further benefit for the "what's built" page: because the staging tree is
disposable, the page has no authored source file at all. There is nothing to
hand-edit and no drift to check — strictly better than the regenerate-and-diff
pattern used elsewhere in this repo.

See notes/docs-v2-spec.md §5 and §6.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.parity.manifest import SITE_DOCS, site_doc_for_path  # noqa: E402

SOURCE_DIR = REPO_ROOT / "docs-site" / "docs"
STAGING_DIR = REPO_ROOT / "docs-site" / ".build"

# Plain markdown, deliberately: a blockquote renders under any generator, while
# an admonition would tie the output to one theme's extension set.
BADGE_TEXT: dict[str, str] = {
    "deployed": "**Available now**",
    "in_progress": "**Being built** — this page describes work in progress.",
    "roadmap": "**Not built yet** — designed for, not available.",
    "non_goal": "**Not planned** — here's why.",
}

STATUS_ORDER: tuple[str, ...] = ("deployed", "in_progress", "roadmap", "non_goal")

SECTION_HEADING: dict[str, str] = {
    "deployed": "Available now",
    "in_progress": "Being built",
    "roadmap": "Not built yet",
    "non_goal": "Not planned",
}

_H1 = re.compile(r"^#\s+.+$", re.MULTILINE)


def _inject_badge(text: str, status: str) -> str:
    """Insert the status badge immediately after the page's first H1."""
    badge = BADGE_TEXT.get(status)
    if badge is None:
        return text
    match = _H1.search(text)
    if match is None:
        # No H1 to anchor to; put the badge at the top rather than dropping it.
        return f"> {badge}\n\n{text}"
    end = match.end()
    return f"{text[:end]}\n\n> {badge}\n{text[end:]}"


def _render_whats_built() -> str:
    """Render the generated status page from SITE_DOCS."""
    lines = [
        "---",
        "title: What's built and what isn't",
        "generated: true",
        "---",
        "",
        "# What's built and what isn't",
        "",
        "This page is generated from the project's own parity manifest, not",
        "written by hand — so it cannot quietly go stale. If something below is",
        "marked available, the code for it exists.",
        "",
    ]
    for status in STATUS_ORDER:
        rows = [d for d in SITE_DOCS if d.status == status]
        if not rows:
            continue
        lines.append(f"## {SECTION_HEADING[status]}")
        lines.append("")
        for doc in sorted(rows, key=lambda d: d.label):
            # This page lives at reference/, so guides/x.md is ../guides/x.md.
            if doc.path:
                lines.append(f"- [{doc.label}](../{doc.path})")
            else:
                lines.append(f"- {doc.label}")
        lines.append("")
    return "\n".join(lines)


def stage(source: Path, staging: Path) -> tuple[int, int]:
    """Stage the tree. Returns (pages staged, badges injected)."""
    if not source.is_dir():
        raise SystemExit(f"error: source directory not found: {source}")

    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(source, staging)

    badged = 0
    for page in sorted(staging.rglob("*.md")):
        rel = page.relative_to(staging).as_posix()
        if not rel.startswith("guides/"):
            continue
        doc = site_doc_for_path(rel)
        if doc is None:
            # test_docs_status.py R5 fails on this; skip rather than guess.
            continue
        page.write_text(
            _inject_badge(page.read_text(encoding="utf-8"), doc.status),
            encoding="utf-8",
        )
        badged += 1

    reference = staging / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    (reference / "whats-built.md").write_text(_render_whats_built(), encoding="utf-8")

    pages = sorted(staging.rglob("*.md"))
    return len(pages), badged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--source", type=Path, default=SOURCE_DIR, help="authored markdown tree"
    )
    parser.add_argument(
        "--staging", type=Path, default=STAGING_DIR, help="generated output tree"
    )
    args = parser.parse_args()

    count, badged = stage(args.source, args.staging)
    rel = args.staging.relative_to(REPO_ROOT)
    print(f"OK: staged {count} page(s) to {rel}; {badged} status badge(s) injected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
