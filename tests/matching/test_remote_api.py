"""Opt-in remote API probe — set OHM_API_BASE to a live OHM origin.

Documents the gap between harness okh_manifest matches (works) and stored
okh_id matches when manufacturing_processes is empty (fails).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

import pytest

from tests.matching.fixtures import __file__ as _fixtures_sentinel  # noqa: F401

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _api_base() -> str | None:
    raw = os.environ.get("OHM_API_BASE", "").strip().rstrip("/")
    return raw or None


pytestmark = [
    pytest.mark.allow_network,
    pytest.mark.skipif(
        not _api_base(),
        reason="Set OHM_API_BASE=https://… to probe a live OHM API",
    ),
]


def _get(path: str, timeout: float = 120) -> dict[str, Any]:
    base = _api_base()
    assert base
    with urllib.request.urlopen(f"{base}{path}", timeout=timeout) as resp:
        return json.load(resp)


def _post(path: str, body: dict[str, Any], timeout: float = 180) -> dict[str, Any]:
    base = _api_base()
    assert base
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def test_remote_health_and_mom_pool():
    health = _get("/health")
    assert health.get("status") == "ok"
    spaces = _get("/v1/api/okw/spaces?include_mom=true")
    assert spaces.get("mom_available") is True
    assert (spaces.get("mom_count") or 0) > 0
    print(
        f"\nremote health version={health.get('version')} "
        f"okh={health.get('storage', {}).get('okh_count')} "
        f"okw={health.get('storage', {}).get('okw_count')} "
        f"mom_spaces={spaces.get('mom_count')} local_spaces={spaces.get('local_count')}"
    )


def test_remote_harness_manifest_matches_3dp():
    """Inline 3DP okh_manifest against MoM must return solutions (id-alignment OK)."""
    with open(os.path.join(FIXTURES, "okh_3dp_only.json"), encoding="utf-8") as f:
        okh = json.load(f)
    spaces = _get("/v1/api/okw/spaces?include_mom=true")["spaces"]
    iri = next(s["id"] for s in spaces if "3d_printing" in (s.get("processes") or []))
    data = _post(
        "/v1/api/match",
        {
            "okh_manifest": okh,
            "network_filter": {"include_mom": True},
            "okw_ids": [iri],
            "max_results": 10,
            "save_solution": False,
            "min_confidence": 0.1,
            "include_human_summary": False,
        },
    )["data"]
    assert (data.get("total_solutions") or 0) >= 1
    print(f"\nharness okh_manifest + MoM IRI → solutions={data.get('total_solutions')}")


def test_remote_stored_okh_empty_processes_yield_zero(capsys):
    """UI path: many stored OKHs have empty manufacturing_processes → 0 matches."""
    listing = _get("/v1/api/okh?page=1&page_size=25")
    items = listing.get("items") or []
    assert items, "live OKH catalog empty"

    empty = 0
    sampled = 0
    for it in items[:20]:
        oid = it["id"]
        try:
            detail = _get(f"/v1/api/okh/{oid}")
        except urllib.error.HTTPError:
            continue
        sampled += 1
        procs = detail.get("manufacturing_processes") or []
        if not procs:
            empty += 1

    print(
        f"\nstored OKH sample: {sampled} details, "
        f"{empty} with empty manufacturing_processes "
        f"({100 * empty / max(sampled, 1):.0f}%)"
    )
    assert sampled > 0
    # Soft informational assert: flag when the catalog is largely process-empty.
    if empty == sampled:
        print(
            "DIAGNOSIS: all sampled stored OKHs lack manufacturing_processes. "
            "Match UI uses okh_id → extractor finds no requirements → 0 solutions. "
            "Harness okh_manifest with explicit ['3DP'] still matches MoM."
        )

    # Prove one empty OKH yields zero solutions against known-good MoM 3DP subset.
    empty_id = next(
        it["id"]
        for it in items
        if not (_get(f"/v1/api/okh/{it['id']}").get("manufacturing_processes") or [])
    )
    spaces = _get("/v1/api/okw/spaces?include_mom=true")["spaces"]
    only3 = [s["id"] for s in spaces if "3d_printing" in (s.get("processes") or [])][
        :20
    ]
    data = _post(
        "/v1/api/match",
        {
            "okh_id": empty_id,
            "network_filter": {"include_mom": True},
            "okw_ids": only3,
            "max_results": 10,
            "save_solution": False,
            "min_confidence": 0.1,
            "quality_level": "professional",
            "strict_mode": False,
            "include_human_summary": False,
        },
    )["data"]
    assert (data.get("total_solutions") or 0) == 0
    print(
        f"stored okh_id={empty_id} vs 20 MoM 3DP spaces → "
        f"solutions={data.get('total_solutions')} (expected 0)"
    )
