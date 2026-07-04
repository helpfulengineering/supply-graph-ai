"""Unit tests for reverse matching — designs a facility can produce (review #7).

`find_designs_for_facility` runs the existing per-facility matcher once per
candidate design (single-facility pool) and returns the designs that clear the
confidence threshold, ranked by confidence.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _manifest(okh_id: str, title: str):
    return SimpleNamespace(id=okh_id, title=title)


def _sol(score: float):
    return SimpleNamespace(score=score)


async def _service_with_scores(monkeypatch, scores_by_id):
    """Build a MatchingService whose per-design match returns preset scores."""
    from src.core.services.matching_service import MatchingService

    service = MatchingService()
    monkeypatch.setattr(service, "ensure_initialized", AsyncMock())

    async def fake_match(manifest, facilities, explicit_domain=None):
        sols = scores_by_id.get(manifest.id, [])
        # Real matcher returns a Set[SupplyTreeSolution]; a list suffices here
        # (find_designs_for_facility only iterates), and avoids hashing the
        # unhashable SimpleNamespace stand-ins.
        return [_sol(s) for s in sols]

    monkeypatch.setattr(service, "find_matches_with_manifest", fake_match)
    return service


@pytest.mark.asyncio
async def test_ranks_matched_designs_by_confidence(monkeypatch):
    service = await _service_with_scores(
        monkeypatch,
        {"a": [0.6], "b": [0.9], "c": [0.75]},
    )
    facility = SimpleNamespace(name="FabLab")

    designs = await service.find_designs_for_facility(
        facility,
        [_manifest("a", "A"), _manifest("b", "B"), _manifest("c", "C")],
    )

    assert [d["okh_id"] for d in designs] == ["b", "c", "a"]
    assert [d["rank"] for d in designs] == [1, 2, 3]
    assert designs[0]["okh_title"] == "B"


@pytest.mark.asyncio
async def test_drops_designs_below_min_confidence(monkeypatch):
    service = await _service_with_scores(monkeypatch, {"a": [0.2], "b": [0.9]})
    facility = SimpleNamespace(name="FabLab")

    designs = await service.find_designs_for_facility(
        facility,
        [_manifest("a", "A"), _manifest("b", "B")],
        min_confidence=0.5,
    )

    assert [d["okh_id"] for d in designs] == ["b"]


@pytest.mark.asyncio
async def test_drops_designs_with_no_solution(monkeypatch):
    service = await _service_with_scores(monkeypatch, {"a": [], "b": [0.8]})
    facility = SimpleNamespace(name="FabLab")

    designs = await service.find_designs_for_facility(
        facility, [_manifest("a", "A"), _manifest("b", "B")]
    )

    assert [d["okh_id"] for d in designs] == ["b"]


@pytest.mark.asyncio
async def test_max_results_caps_the_ranked_list(monkeypatch):
    service = await _service_with_scores(
        monkeypatch, {"a": [0.6], "b": [0.9], "c": [0.75]}
    )
    facility = SimpleNamespace(name="FabLab")

    designs = await service.find_designs_for_facility(
        facility,
        [_manifest("a", "A"), _manifest("b", "B"), _manifest("c", "C")],
        max_results=2,
    )

    assert [d["okh_id"] for d in designs] == ["b", "c"]


@pytest.mark.asyncio
async def test_uses_best_solution_score_per_design(monkeypatch):
    service = await _service_with_scores(monkeypatch, {"a": [0.3, 0.85, 0.5]})
    facility = SimpleNamespace(name="FabLab")

    designs = await service.find_designs_for_facility(facility, [_manifest("a", "A")])

    assert designs[0]["confidence"] == 0.85
