#!/usr/bin/env python3
"""
Evaluate chunked LLM canary quality gates against a baseline batch report.

This compares two batch report JSON files produced by `okh_generation_batch.py`:
- baseline report (typically 4L with chunked mode disabled)
- candidate report (typically 4L with chunked mode enabled)

Usage:
    conda activate supply-graph-ai
    python scripts/okh_generation_chunked_evaluation.py \
      --baseline tests/data/okh_generation/last_batch_report_baseline_4l.json \
      --candidate tests/data/okh_generation/last_batch_report_chunked_4l.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_report(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _row_map(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in report.get("repos", []):
        rid = row.get("id")
        if isinstance(rid, str) and rid:
            out[rid] = row
    return out


def _field_presence_score(heur: Dict[str, Any]) -> float:
    # Proxy required-field completeness from currently available heuristic flags.
    keys = ["has_title", "has_version", "has_function", "has_description"]
    vals = [1.0 if bool(heur.get(k)) else 0.0 for k in keys]
    return sum(vals) / len(vals)


def _summarize(report: Dict[str, Any]) -> Dict[str, Any]:
    rows = report.get("repos", [])
    total = len(rows)
    ok_rows = [r for r in rows if r.get("status") == "ok"]
    err_rows = [r for r in rows if r.get("status") == "error"]
    ok_count = len(ok_rows)
    error_count = len(err_rows)

    if ok_rows:
        avg_seconds = sum(float(r.get("seconds", 0.0)) for r in ok_rows) / ok_count
        avg_conf = (
            sum(
                float(
                    (r.get("heuristic_quality") or {}).get("generation_confidence", 0.0)
                )
                for r in ok_rows
            )
            / ok_count
        )
        avg_presence = (
            sum(
                _field_presence_score(r.get("heuristic_quality") or {}) for r in ok_rows
            )
            / ok_count
        )
    else:
        avg_seconds = 0.0
        avg_conf = 0.0
        avg_presence = 0.0

    return {
        "total_rows": total,
        "ok_rows": ok_count,
        "error_rows": error_count,
        "error_rate": (error_count / total) if total else 0.0,
        "avg_seconds_ok_rows": avg_seconds,
        "avg_generation_confidence": avg_conf,
        "avg_required_field_presence_proxy": avg_presence,
    }


def _paired_ids(
    baseline: Dict[str, Dict[str, Any]], candidate: Dict[str, Dict[str, Any]]
) -> List[str]:
    return sorted(set(baseline.keys()) & set(candidate.keys()))


def _compare_paired(
    baseline_rows: Dict[str, Dict[str, Any]], candidate_rows: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    ids = _paired_ids(baseline_rows, candidate_rows)
    if not ids:
        return {
            "paired_count": 0,
            "avg_latency_delta_seconds": 0.0,
            "avg_confidence_delta": 0.0,
            "avg_presence_proxy_delta": 0.0,
        }

    lat_deltas: List[float] = []
    conf_deltas: List[float] = []
    pres_deltas: List[float] = []
    for rid in ids:
        b = baseline_rows[rid]
        c = candidate_rows[rid]
        lat_deltas.append(float(c.get("seconds", 0.0)) - float(b.get("seconds", 0.0)))
        bq = b.get("heuristic_quality") or {}
        cq = c.get("heuristic_quality") or {}
        conf_deltas.append(
            float(cq.get("generation_confidence", 0.0))
            - float(bq.get("generation_confidence", 0.0))
        )
        pres_deltas.append(_field_presence_score(cq) - _field_presence_score(bq))

    return {
        "paired_count": len(ids),
        "avg_latency_delta_seconds": sum(lat_deltas) / len(lat_deltas),
        "avg_confidence_delta": sum(conf_deltas) / len(conf_deltas),
        "avg_presence_proxy_delta": sum(pres_deltas) / len(pres_deltas),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "tests/data/okh_generation/chunked_evaluation_report.json",
    )
    parser.add_argument("--stdout", action="store_true", help="Print JSON report only")
    parser.add_argument(
        "--max-error-rate-increase",
        type=float,
        default=0.0,
        help="Allowed increase in error rate vs baseline",
    )
    parser.add_argument(
        "--max-latency-ratio",
        type=float,
        default=2.5,
        help="Allowed candidate avg latency / baseline avg latency ratio",
    )
    parser.add_argument(
        "--min-confidence-delta",
        type=float,
        default=-0.05,
        help="Minimum allowed delta for avg generation confidence (candidate - baseline)",
    )
    parser.add_argument(
        "--min-presence-proxy-delta",
        type=float,
        default=-0.05,
        help="Minimum allowed delta for required-field presence proxy (allow small LLM-run variance)",
    )
    args = parser.parse_args()

    baseline = _load_report(args.baseline)
    candidate = _load_report(args.candidate)

    baseline_summary = _summarize(baseline)
    candidate_summary = _summarize(candidate)

    base_rows = _row_map(baseline)
    cand_rows = _row_map(candidate)
    paired = _compare_paired(base_rows, cand_rows)

    error_rate_increase = (
        candidate_summary["error_rate"] - baseline_summary["error_rate"]
    )
    baseline_avg_latency = baseline_summary["avg_seconds_ok_rows"]
    candidate_avg_latency = candidate_summary["avg_seconds_ok_rows"]
    latency_ratio = (
        (candidate_avg_latency / baseline_avg_latency)
        if baseline_avg_latency > 0
        else 0.0
    )

    gates = {
        "schema_and_reliability": {
            "pass": error_rate_increase <= args.max_error_rate_increase,
            "error_rate_increase": error_rate_increase,
            "max_allowed": args.max_error_rate_increase,
        },
        "extraction_quality_confidence": {
            "pass": paired["avg_confidence_delta"] >= args.min_confidence_delta,
            "avg_confidence_delta": paired["avg_confidence_delta"],
            "min_allowed": args.min_confidence_delta,
        },
        "extraction_quality_presence_proxy": {
            "pass": paired["avg_presence_proxy_delta"] >= args.min_presence_proxy_delta,
            "avg_presence_proxy_delta": paired["avg_presence_proxy_delta"],
            "min_allowed": args.min_presence_proxy_delta,
        },
        "efficiency_latency": {
            "pass": latency_ratio <= args.max_latency_ratio,
            "latency_ratio": latency_ratio,
            "max_allowed": args.max_latency_ratio,
        },
    }

    all_pass = all(bool(g["pass"]) for g in gates.values())
    report = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline_report": str(args.baseline),
        "candidate_report": str(args.candidate),
        "baseline_summary": baseline_summary,
        "candidate_summary": candidate_summary,
        "paired_deltas": paired,
        "quality_gates": gates,
        "all_gates_pass": all_pass,
        "notes": [
            "required_field_presence_proxy uses currently available heuristic flags",
            "stability gate (run-to-run variance) should be evaluated across repeated runs",
        ],
    }

    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.stdout:
        print(text, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
        print(json.dumps({"all_gates_pass": all_pass}, indent=2), file=sys.stderr)

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
