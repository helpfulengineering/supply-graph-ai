#!/usr/bin/env python3
"""Generate ``PROCESS_DEFINITIONS`` from ``src/config/taxonomy/processes.yaml``.

The process taxonomy exists in two places:

  * ``src/config/taxonomy/processes.yaml`` — the live source of truth
  * ``src/core/taxonomy/process_taxonomy.py`` → ``PROCESS_DEFINITIONS`` — the
    fallback ``_create_taxonomy()`` uses when the YAML is missing or invalid

They were hand-synchronised across 49 processes with nothing asserting they
agreed, so adding a process meant remembering two files; miss one and the
fallback silently serves a different taxonomy from production.

Generating at COMMIT time rather than import time is deliberate. Deriving the
literal at import would mean a corrupt YAML leaves no fallback at all — removing
the safety net exactly when it is needed. Keeping it checked in preserves a real
fallback while making drift impossible.

Usage:
    uv run python scripts/generate_process_definitions.py            # write
    uv run python scripts/generate_process_definitions.py --check    # gate
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TARGET = REPO_ROOT / "src" / "core" / "taxonomy" / "process_taxonomy.py"
YAML_PATH = REPO_ROOT / "src" / "config" / "taxonomy" / "processes.yaml"

DECLARATION = "PROCESS_DEFINITIONS: List[ProcessDefinition] = ["

HEADER = f"""{DECLARATION}
    # ------------------------------------------------------------------
    # GENERATED — do not edit by hand.
    #
    # Source of truth: src/config/taxonomy/processes.yaml
    # Regenerate:      uv run python scripts/generate_process_definitions.py
    # Verified by:     make ready (taxonomy-check)
    #
    # This literal is the fallback used when the YAML is missing or invalid,
    # so it stays checked in rather than being derived at import time.
    # ------------------------------------------------------------------"""


def _render(definitions) -> str:
    """Render the definitions as the Python list literal."""
    lines = [HEADER]
    for d in definitions:
        lines.append("    ProcessDefinition(")
        lines.append(f"        canonical_id={d.canonical_id!r},")
        lines.append(f"        display_name={d.display_name!r},")
        lines.append(f"        tsdc_code={d.tsdc_code!r},")
        lines.append(f"        parent={d.parent!r},")
        if d.aliases:
            lines.append("        aliases=frozenset(")
            lines.append("            {")
            # Sorted so regeneration is deterministic; a set has no order.
            for alias in sorted(d.aliases):
                lines.append(f"                {alias!r},")
            lines.append("            }")
            lines.append("        ),")
        else:
            lines.append("        aliases=frozenset(),")
        if d.wikidata_qid:
            lines.append(f"        wikidata_qid={d.wikidata_qid!r},")
        lines.append("    ),")
    lines.append("]")
    return "\n".join(lines)


def _splice(source: str, rendered: str) -> str:
    """Replace the existing literal with the rendered one, black-formatted.

    Formatting here rather than leaving it to `make format` is what makes
    `--check` meaningful: otherwise the formatter rewrites the generated block,
    the generator disagrees with what is on disk, and the gate fails on every
    run even though nothing drifted.
    """
    import black

    start = source.index(DECLARATION)
    # The literal ends at the first line that is exactly "]" at column zero.
    end = source.index("\n]\n", start) + len("\n]\n")
    updated = source[:start] + rendered + "\n" + source[end:]
    return black.format_str(updated, mode=black.Mode())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the checked-in literal differs from the YAML.",
    )
    args = parser.parse_args()

    from src.core.taxonomy.process_taxonomy import load_from_yaml

    definitions = load_from_yaml(YAML_PATH)
    source = TARGET.read_text(encoding="utf-8")
    updated = _splice(source, _render(definitions))

    if args.check:
        if updated != source:
            print(
                "DRIFT: PROCESS_DEFINITIONS does not match "
                "src/config/taxonomy/processes.yaml.\n"
                "The YAML is the source of truth; the Python literal is its "
                "generated fallback.\n"
                "Fix: uv run python scripts/generate_process_definitions.py",
                file=sys.stderr,
            )
            return 1
        print(
            f"OK: PROCESS_DEFINITIONS matches processes.yaml ({len(definitions)} processes)"
        )
        return 0

    if updated == source:
        print(f"OK: already current ({len(definitions)} processes)")
        return 0

    TARGET.write_text(updated, encoding="utf-8")
    print(
        f"Wrote {len(definitions)} processes to "
        f"{TARGET.relative_to(REPO_ROOT)} from {YAML_PATH.relative_to(REPO_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
