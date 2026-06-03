"""A/B debug-trace regression for current vs baseline-like route behavior."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.mark.quarantine
@pytest.mark.asyncio
async def test_debug_trace_mode_compares_prefilter_and_early_stop(monkeypatch):
    from src.core.api.models.match.request import MatchRequest
    from src.core.api.routes import match as match_mod

    class FakeOKHManifest:
        pass

    monkeypatch.setattr(match_mod, "OKHManifest", FakeOKHManifest)
    monkeypatch.setattr(
        match_mod,
        "_detect_domain_from_request",
        AsyncMock(return_value="manufacturing"),
    )
    monkeypatch.setattr(
        match_mod,
        "_extract_okh_manifest",
        AsyncMock(return_value=FakeOKHManifest()),
    )
    monkeypatch.setattr(
        match_mod,
        "_extract_required_processes_from_manifest",
        lambda _m: ["laser cutting", "anodizing"],
    )

    facilities_pool = [
        {
            "id": "fac-1",
            "name": "Facility 1",
            "capabilities": [{"process_name": "laser cutting"}],
        },
        {
            "id": "fac-2",
            "name": "Facility 2",
            "capabilities": [{"process_name": "anodizing"}],
        },
        {
            "id": "fac-3",
            "name": "Facility 3",
            "capabilities": [{"process_name": "laser cutting"}],
        },
    ]
    monkeypatch.setattr(
        match_mod,
        "_get_filtered_facilities",
        AsyncMock(return_value=facilities_pool),
    )
    monkeypatch.setattr(
        match_mod,
        "get_matching_service",
        AsyncMock(return_value=object()),
    )

    capture: list[dict] = []

    async def fake_perform(
        _svc,
        _requirements_data,
        facilities,
        request,
        _request_id,
        domain="manufacturing",
    ):
        capture.append(
            {
                "mode": request.debug_trace_mode,
                "facility_count_seen": len(facilities),
                "max_results_seen": request.max_results,
                "domain": domain,
            }
        )
        return [{"facility_id": "fac-1", "tree": {"match_type": "direct"}}]

    monkeypatch.setattr(match_mod, "_perform_enhanced_matching", fake_perform)
    monkeypatch.setattr(
        match_mod,
        "_process_matching_results",
        AsyncMock(
            return_value=[{"facility_id": "fac-1", "tree": {"match_type": "direct"}}]
        ),
    )
    monkeypatch.setattr(
        match_mod,
        "_validate_results",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        match_mod, "_collect_matched_processes_from_solutions", lambda _s: set()
    )
    monkeypatch.setattr(
        match_mod,
        "_build_match_summary",
        lambda **_kwargs: ({"coverage_ratio": 1.0}, []),
    )
    monkeypatch.setattr(match_mod, "render_match_summary", lambda _m: "ok")
    monkeypatch.setattr(
        match_mod, "_build_match_suggestions", lambda **_kwargs: ([], [])
    )
    monkeypatch.setattr(
        match_mod, "_build_optional_human_summary", lambda **_kwargs: None
    )

    http_request = SimpleNamespace(state=SimpleNamespace(request_id="unit-test"))

    current_req = MatchRequest.model_construct(
        okh_manifest={"title": "dummy"},
        max_candidate_facilities=1,
        max_results=1,
        debug_trace=True,
        debug_trace_mode="current",
    )
    baseline_req = MatchRequest.model_construct(
        okh_manifest={"title": "dummy"},
        max_candidate_facilities=1,
        max_results=1,
        debug_trace=True,
        debug_trace_mode="baseline",
    )

    current_resp = await match_mod.match_requirements_to_capabilities(
        current_req, http_request, storage_service=None
    )
    baseline_resp = await match_mod.match_requirements_to_capabilities(
        baseline_req, http_request, storage_service=None
    )
    current_payload = current_resp.get("data", current_resp)
    baseline_payload = baseline_resp.get("data", baseline_resp)

    assert current_payload["debug_trace"]["prefilter_applied"] is True
    assert baseline_payload["debug_trace"]["prefilter_applied"] is False
    assert current_payload["debug_trace"]["facilities_after_prefilter_count"] == 1
    assert baseline_payload["debug_trace"]["facilities_after_prefilter_count"] == 3
    assert current_payload["debug_trace"]["max_results_effective"] == 1
    assert baseline_payload["debug_trace"]["max_results_effective"] is None

    assert capture[0]["facility_count_seen"] == 1
    assert capture[1]["facility_count_seen"] == 3
    assert capture[0]["max_results_seen"] == 1
    assert capture[1]["max_results_seen"] is None
