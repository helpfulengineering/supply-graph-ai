"""
Regression baseline for MatchingService layer orchestration (real initialize + call).

Uses a minimal requirement/capability pair so tests exercise the actual cascade code paths.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


@pytest.mark.asyncio
async def test_matching_baseline_identical_process_matches_direct():
    """Frozen fixture: identical processes should satisfy via direct layer."""
    fixture_path = os.path.join(
        _REPO_ROOT, "tests", "fixtures", "matching_baseline.json"
    )
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    from src.core.models.match_explanation import MatchLayer
    from src.core.services.matching_service import MatchingService

    svc = MatchingService()
    await svc.initialize()

    ok, details = await svc._can_satisfy_requirements_with_details(
        data["requirements"],
        data["capabilities"],
        domain=data["domain"],
    )
    assert ok == data["expected_satisfied"]
    assert len(details) == data["expected_detail_count"]
    assert details[0].matching_layer == MatchLayer.DIRECT


@pytest.mark.asyncio
async def test_nlp_veto_suppresses_fuzzy_direct_when_similarity_low():
    """With veto on and low NLP similarity, fuzzy substring direct match must not stand alone."""
    from unittest.mock import AsyncMock, patch

    from src.core.models.match_explanation import MatchStatus
    from src.core.services.matching_service import MatchingService

    svc = MatchingService()
    await svc.initialize()

    async def low_sim(*_a, **_k):
        return 0.05

    svc._nlp_semantic_similarity_for_pair = low_sim
    svc._heuristic_match_with_rule = AsyncMock(return_value=(False, None))
    svc._nlp_match = AsyncMock(return_value=False)

    # Non-taxonomy substring match (fuzzy direct): xyzfoo ⊂ xyzfoobar — distinct canonical IDs.
    with (
        patch(
            "src.core.services.matching_service.MATCHING_NLP_VETO_ENABLED",
            True,
        ),
        patch(
            "src.core.services.matching_service.MATCHING_NLP_VETO_THRESHOLD",
            0.2,
        ),
    ):
        ok, details = await svc._can_satisfy_requirements_with_details(
            [{"process_name": "xyzfoo"}],
            [{"process_name": "xyzfoobar"}],
            domain="manufacturing",
        )

    assert ok is False
    assert details and details[0].status == MatchStatus.NOT_MATCHED
