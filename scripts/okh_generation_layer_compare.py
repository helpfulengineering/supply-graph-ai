#!/usr/bin/env python3
"""
Compare 3-layer vs 4-layer OKH manifests on disk (heuristic metrics).

For each supported repo in tests/data/okh_generation/repositories.json, if both
3L and 4L manifests exist for that repo's clone URL (title-slug or legacy
``<id>-<layer>.json`` names), computes ``metrics.heuristic_layer_comparison``
and writes a JSON report.

Usage:
    conda activate supply-graph-ai
    python scripts/okh_generation_layer_compare.py
    python scripts/okh_generation_layer_compare.py --stdout
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repositories-json",
        type=Path,
        default=REPO_ROOT / "tests/data/okh_generation/repositories.json",
    )
    parser.add_argument(
        "--clones-dir",
        type=Path,
        default=REPO_ROOT / "tests/data/okh_generation/clones",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "docs/metrics/okh_generation_3l_vs_4l.json",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print JSON to stdout only",
    )
    args = parser.parse_args()

    from tests.data.okh_generation.baseline_report import load_repositories_dataset
    from tests.data.okh_generation.manifest_discovery import (
        find_generated_manifest_path,
    )
    from tests.data.okh_generation.metrics import heuristic_layer_comparison

    data = load_repositories_dataset(args.repositories_json)
    rows: List[Dict[str, Any]] = []
    both_count = 0

    for repo in data.get("repos", []):
        if not repo.get("platform_supported"):
            continue
        rid = repo.get("id", "")
        url = repo.get("url") or ""
        p3 = find_generated_manifest_path(args.clones_dir, "3L", url, dataset_id=rid)
        p4 = find_generated_manifest_path(args.clones_dir, "4L", url, dataset_id=rid)
        row: Dict[str, Any] = {"id": rid, "url": repo.get("url")}
        if p3 is None or not p3.is_file():
            row["status"] = "missing_3L"
            rows.append(row)
            continue
        if p4 is None or not p4.is_file():
            row["status"] = "missing_4L"
            rows.append(row)
            continue
        with p3.open(encoding="utf-8") as f:
            m3 = json.load(f)
        with p4.open(encoding="utf-8") as f:
            m4 = json.load(f)
        row["status"] = "compared"
        row["comparison"] = heuristic_layer_comparison(m3, m4)
        both_count += 1
        rows.append(row)

    report = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pairs_compared": both_count,
        "repos": rows,
    }
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"

    if args.stdout:
        print(text, end="")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"Wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
