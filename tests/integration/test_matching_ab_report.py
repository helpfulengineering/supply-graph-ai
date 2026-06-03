"""
Integration A/B report for matching behavior classification.

Runs the same `/v1/api/match` request twice:
- mode=current   (prefilter + max_results)
- mode=baseline  (prefilter/early-stop disabled via debug mode)

Produces a compact metrics report and classifies observed behavior as:
`improvement`, `drift`, or `regression`.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

import pytest
import requests


def _base_url() -> str:
    return (
        os.getenv("MATCH_AB_BASE_URL")
        or os.getenv("SERVICE_URL")
        or os.getenv("BASE_URL")
        or ""
    ).rstrip("/")


def _auth_headers() -> Dict[str, str]:
    token = os.getenv("IDENTITY_TOKEN") or os.getenv("API_KEY") or ""
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _extract_payload(resp_json: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(resp_json.get("data"), dict):
        return resp_json["data"]
    return resp_json


def _top_unique_ids(solutions: List[Dict[str, Any]], k: int = 10) -> List[str]:
    out: List[str] = []
    seen = set()
    for s in solutions:
        fid = s.get("facility_id")
        if fid is None:
            continue
        fid_s = str(fid)
        if fid_s in seen:
            continue
        seen.add(fid_s)
        out.append(fid_s)
        if len(out) >= k:
            break
    return out


def _coverage_ratio(payload: Dict[str, Any]) -> float:
    summary = payload.get("match_summary") or {}
    raw = summary.get("coverage_ratio")
    try:
        if raw is not None:
            return float(raw)
    except (TypeError, ValueError):
        pass
    return 0.0


def _post_match(base_url: str, mode: str) -> Dict[str, Any]:
    body = {
        "okh_manifest": {
            "title": "AB report prosthetic-like probe",
            "version": "1.0.0",
            "license": {"hardware": "MIT", "documentation": "MIT", "software": "MIT"},
            "licensor": "A/B Integration Test",
            "documentation_language": "en",
            "function": "Compare matching behavior against baseline mode",
            "manufacturing_processes": [
                "3D Printing",
                "CNC Machining",
                "Assembly",
            ],
        },
        "max_results": 10,
        "debug_trace": True,
        "debug_trace_mode": mode,
    }
    url = f"{base_url}/v1/api/match"
    response = requests.post(url, json=body, headers=_auth_headers(), timeout=120)
    if response.status_code >= 400:
        raise AssertionError(
            f"POST {url} failed with {response.status_code}: {response.text[:1500]}"
        )
    data = response.json()
    payload = _extract_payload(data)
    assert isinstance(
        payload.get("debug_trace"), dict
    ), "debug_trace missing from payload"
    return payload


def _classify(
    current: Dict[str, Any], baseline: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    current_solutions = current.get("solutions") or []
    baseline_solutions = baseline.get("solutions") or []
    current_top = _top_unique_ids(current_solutions, k=10)
    baseline_top = _top_unique_ids(baseline_solutions, k=10)
    overlap = len(set(current_top).intersection(set(baseline_top)))
    denom = max(1, len(set(current_top).union(set(baseline_top))))
    top_jaccard = overlap / denom

    curr_cov = _coverage_ratio(current)
    base_cov = _coverage_ratio(baseline)
    curr_time = float(current.get("processing_time") or 0.0)
    base_time = float(baseline.get("processing_time") or 0.0)

    if curr_cov + 1e-9 < base_cov:
        label = "regression"
    elif (
        curr_cov + 1e-9 >= base_cov
        and (curr_time <= (base_time * 1.10) if base_time > 0 else True)
        and top_jaccard >= 0.25
    ):
        label = "improvement"
    else:
        label = "drift"

    report = {
        "classification": label,
        "current": {
            "solutions": len(current_solutions),
            "unique_top_ids": len(current_top),
            "coverage_ratio": curr_cov,
            "processing_time": curr_time,
            "trace": current.get("debug_trace") or {},
        },
        "baseline": {
            "solutions": len(baseline_solutions),
            "unique_top_ids": len(baseline_top),
            "coverage_ratio": base_cov,
            "processing_time": base_time,
            "trace": baseline.get("debug_trace") or {},
        },
        "delta": {
            "coverage_ratio": curr_cov - base_cov,
            "processing_time": curr_time - base_time,
            "top10_jaccard": top_jaccard,
            "top10_overlap_count": overlap,
        },
    }
    return label, report


@pytest.mark.integration
def test_matching_ab_report_remote_okw():
    """
    Integration classification test.

    Requires:
    - running API endpoint (local or remote)
    - MATCH_AB_BASE_URL (or SERVICE_URL / BASE_URL)
    """
    base_url = _base_url()
    if not base_url:
        pytest.skip(
            "Set MATCH_AB_BASE_URL (or SERVICE_URL/BASE_URL) to run A/B report test"
        )

    current = _post_match(base_url, "current")
    baseline = _post_match(base_url, "baseline")
    label, report = _classify(current, baseline)

    print("\nA/B match report:\n" + json.dumps(report, indent=2, sort_keys=True))
    assert label in {"improvement", "drift", "regression"}

    fail_on_regression = (
        os.getenv("MATCH_AB_FAIL_ON_REGRESSION", "false").lower() == "true"
    )
    if fail_on_regression:
        assert label != "regression", json.dumps(report, indent=2, sort_keys=True)
