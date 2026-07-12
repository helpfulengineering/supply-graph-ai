"""Load the canary repository dataset and build offline baseline reports."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .manifest_discovery import find_generated_manifest_path
from .metrics import heuristic_manifest_quality

BLOCKING_FIELDS = ("title", "version", "function")


def load_repositories_dataset(path: Path) -> Dict[str, Any]:
    """Load ``repositories.json`` and require a ``repos`` list."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("repos"), list):
        raise ValueError(f"Invalid repositories dataset: {path}")
    return data


def build_baseline_report(
    repo_root: Path,
    *,
    layer: str = "3L",
    repositories_json: Path,
    manifests_dir: Path,
) -> Dict[str, Any]:
    """Compare generated manifests to ground truth where both exist."""
    root = Path(repo_root).resolve()
    data = load_repositories_dataset(repositories_json)
    manifests_dir = Path(manifests_dir)

    rows: List[Dict[str, Any]] = []
    counts: Dict[str, int] = defaultdict(int)
    compared_accuracy: List[float] = []
    compared_presence: List[float] = []
    by_dq: Dict[str, List[float]] = defaultdict(list)
    by_domain: Dict[str, List[float]] = defaultdict(list)
    materials_near = 0
    materials_prose = 0
    materials_scored = 0

    for repo in data.get("repos", []):
        if not isinstance(repo, dict):
            continue
        rid = str(repo.get("id") or "")
        url = str(repo.get("url") or "")
        row: Dict[str, Any] = {
            "id": rid,
            "url": url,
            "platform": repo.get("platform"),
            "platform_supported": bool(repo.get("platform_supported")),
            "documentation_quality": repo.get("documentation_quality"),
            "domain": repo.get("domain"),
            "project_structure": repo.get("project_structure"),
            "ground_truth_path": repo.get("ground_truth_path"),
        }

        gt_rel = repo.get("ground_truth_path")
        if not gt_rel:
            row["status"] = "skipped_no_ground_truth"
            counts["skipped_no_ground_truth"] += 1
            rows.append(row)
            continue

        gt_path = root / str(gt_rel)
        if not gt_path.is_file():
            row["status"] = "skipped_no_ground_truth"
            row["ground_truth_missing_file"] = True
            counts["skipped_no_ground_truth"] += 1
            rows.append(row)
            continue

        generated = find_generated_manifest_path(
            manifests_dir, layer, url, dataset_id=rid
        )
        row["expected_generated_path"] = _rel_or_str(
            manifests_dir / f"{rid}-{layer}.json", root
        )
        if generated is None or not generated.is_file():
            row["status"] = "skipped_no_generated_manifest"
            counts["skipped_no_generated_manifest"] += 1
            rows.append(row)
            continue

        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        manifest = json.loads(generated.read_text(encoding="utf-8"))
        accuracy, presence = _blocking_scores(gt, manifest)
        heur = heuristic_manifest_quality(manifest)

        row.update(
            {
                "status": "compared",
                "generated_path": _rel_or_str(generated, root),
                "blocking_accuracy": accuracy,
                "blocking_presence_completeness": presence,
                "heuristic_quality": heur,
            }
        )
        counts["compared"] += 1
        compared_accuracy.append(accuracy)
        compared_presence.append(presence)
        dq = str(repo.get("documentation_quality") or "unknown")
        domain = str(repo.get("domain") or "unknown")
        by_dq[dq].append(accuracy)
        by_domain[domain].append(accuracy)
        materials_near += int(heur["materials_near_dup_pairs"])
        materials_prose += int(heur["materials_prose_like_count"])
        materials_scored += 1
        rows.append(row)

    def _avg(vals: List[float]) -> Optional[float]:
        return round(sum(vals) / len(vals), 4) if vals else None

    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repositories_file": _rel_or_str(repositories_json, root),
        "summary": {
            "total_repo_entries": len(data.get("repos", [])),
            "layer": layer,
            "counts_by_status": dict(counts),
            "compared_count": counts.get("compared", 0),
            "avg_blocking_accuracy_compared": _avg(compared_accuracy),
            "avg_blocking_presence_completeness_compared": _avg(compared_presence),
            "materials_heuristics": {
                "manifests_scored": materials_scored,
                "total_near_dup_pairs": materials_near,
                "total_prose_like": materials_prose,
            },
        },
        "by_documentation_quality": {
            k: {"count": len(v), "avg_blocking_accuracy": _avg(v)}
            for k, v in sorted(by_dq.items())
        },
        "by_domain": {
            k: {"count": len(v), "avg_blocking_accuracy": _avg(v)}
            for k, v in sorted(by_domain.items())
        },
        "repos": rows,
    }


def _blocking_scores(
    ground_truth: Dict[str, Any], manifest: Dict[str, Any]
) -> tuple[float, float]:
    fields = list(BLOCKING_FIELDS)
    if "license" in ground_truth:
        fields.append("license")

    matches = 0
    present = 0
    for field in fields:
        gt_val = ground_truth.get(field)
        gen_val = manifest.get(field)
        if _blocking_present(gen_val):
            present += 1
        if _blocking_equal(gt_val, gen_val):
            matches += 1

    n = len(fields) or 1
    return matches / n, present / n


def _blocking_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_blocking_present(v) for v in value.values())
    return True


def _blocking_equal(expected: Any, actual: Any) -> bool:
    if expected is None:
        return True
    if isinstance(expected, str) and isinstance(actual, str):
        return expected.strip().casefold() == actual.strip().casefold()
    if isinstance(expected, dict) and isinstance(actual, dict):
        # License: require overlapping non-empty keys to match case-insensitively
        for key, exp in expected.items():
            if exp is None or exp == "":
                continue
            got = actual.get(key)
            if not _blocking_equal(exp, got):
                return False
        return True
    return expected == actual


def _rel_or_str(path: Path, root: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(root))
    except ValueError:
        return str(path)
