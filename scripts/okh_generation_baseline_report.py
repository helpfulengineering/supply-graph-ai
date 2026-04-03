#!/usr/bin/env python3
"""
Generate OKH generation baseline report (Issue 1.3.1 Phase B5).

Reads tests/data/okh_generation/repositories.json and, for each supported repo
with a ground truth file and a pre-generated manifest at
``tests/data/okh_generation/clones/<repo-id>-<layer>.json`` (default layer ``3L``),
runs the Phase B3 metrics and writes docs/metrics/okh_generation_baseline.json.

Use ``--layer 4L`` to score LLM manifests against the same ground truth (for
experiments). Does not run live generation — use ``scripts/okh_generation_batch.py``
or ``ohm okh generate-from-url`` to produce clone outputs first.

Usage:
    conda activate supply-graph-ai
    python scripts/okh_generation_baseline_report.py
    python scripts/okh_generation_baseline_report.py --output /tmp/baseline.json
    python scripts/okh_generation_baseline_report.py --layer 3L
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write OKH generation baseline JSON from repositories dataset + clone manifests"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "docs/metrics/okh_generation_baseline.json",
        help="Output JSON path (default: docs/metrics/okh_generation_baseline.json)",
    )
    parser.add_argument(
        "--layer",
        default="3L",
        help="Generated manifest suffix layer tag (default: 3L → repo-001-3L.json)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print JSON to stdout only; do not write --output",
    )
    args = parser.parse_args()

    from tests.data.okh_generation.baseline_report import build_baseline_report

    report = build_baseline_report(REPO_ROOT, layer=args.layer)
    text = json.dumps(report, indent=2, ensure_ascii=False)

    if args.stdout:
        print(text)
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text + "\n", encoding="utf-8")
    print(f"Wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
