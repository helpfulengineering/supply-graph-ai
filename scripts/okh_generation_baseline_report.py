#!/usr/bin/env python3
"""
Generate OKH generation baseline report (Issue 1.3.1 Phase B5).

Reads a repositories dataset JSON and, for each repo with a ground truth file
and a pre-generated manifest at ``<manifests-dir>/<repo-id>-<layer>.json``
(default layer ``3L``), runs the Phase B3 metrics and writes a JSON report.

Use ``--layer 4L`` to score LLM manifests against the same ground truth (for
experiments). Does not run live generation — use ``scripts/okh_generation_batch.py``
or ``ohm okh generate-from-url`` to produce manifests first.

Usage:
    conda activate supply-graph-ai
    python scripts/okh_generation_baseline_report.py
    python scripts/okh_generation_baseline_report.py --output /tmp/baseline.json
    python scripts/okh_generation_baseline_report.py --layer 3L \\
        --manifests-dir tmp/oshwa/okh-manifests \\
        --output tmp/oshwa/baseline_report.json
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
        description="Write OKH generation baseline JSON from repositories dataset + generated manifests"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help=(
            "Project root for resolving ground_truth_path entries in repositories.json "
            f"(default: {REPO_ROOT})"
        ),
    )
    parser.add_argument(
        "--repositories-json",
        type=Path,
        default=None,
        help=(
            "Path to repositories.json "
            "(default: <repo-root>/tests/data/okh_generation/repositories.json)"
        ),
    )
    parser.add_argument(
        "--manifests-dir",
        type=Path,
        default=None,
        help=(
            "Directory containing <id>-<layer>.json generated manifests "
            "(default: <repo-root>/tests/data/okh_generation/clones)"
        ),
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
        help="Generated manifest layer tag (default: 3L; filenames use title slug or legacy id)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print JSON to stdout only; do not write --output",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    repositories_json = (
        args.repositories_json.resolve()
        if args.repositories_json is not None
        else repo_root / "tests/data/okh_generation/repositories.json"
    )
    manifests_dir = (
        args.manifests_dir.resolve()
        if args.manifests_dir is not None
        else repo_root / "tests/data/okh_generation/clones"
    )

    from tests.data.okh_generation.baseline_report import build_baseline_report

    report = build_baseline_report(
        repo_root,
        layer=args.layer,
        repositories_json=repositories_json,
        manifests_dir=manifests_dir,
    )
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
