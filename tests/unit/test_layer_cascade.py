"""Unit tests for evaluate_layers and evaluate_layers_supply_tree."""

from __future__ import annotations

import os
import sys

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.core.services.matching._layer_cascade import (
    evaluate_layers,
    evaluate_layers_supply_tree,
)


@pytest.mark.asyncio
async def test_cascade_direct_strong_short_circuits():
    async def direct_eval():
        return True, "strong"

    async def heuristic_eval():
        return True, "rule-x"

    async def nlp_match():
        return True

    async def nlp_sim():
        return 0.99

    ev = await evaluate_layers(
        direct_eval=direct_eval,
        heuristic_eval=heuristic_eval,
        nlp_match=nlp_match,
        nlp_similarity=nlp_sim,
        mode="cascade",
    )
    assert ev.matched and ev.layer == "direct" and ev.direct_path == "strong"


@pytest.mark.asyncio
async def test_cascade_heuristic_when_direct_misses():
    async def direct_eval():
        return False, "none"

    async def heuristic_eval():
        return True, "r1"

    async def nlp_match():
        return True

    async def nlp_sim():
        return 0.5

    ev = await evaluate_layers(
        direct_eval=direct_eval,
        heuristic_eval=heuristic_eval,
        nlp_match=nlp_match,
        nlp_similarity=nlp_sim,
        mode="cascade",
    )
    assert ev.matched and ev.layer == "heuristic" and ev.rule_id == "r1"


@pytest.mark.asyncio
async def test_cascade_nlp_only():
    async def direct_eval():
        return False, "none"

    async def heuristic_eval():
        return False, None

    async def nlp_match():
        return True

    async def nlp_sim():
        return 0.8

    ev = await evaluate_layers(
        direct_eval=direct_eval,
        heuristic_eval=heuristic_eval,
        nlp_match=nlp_match,
        nlp_similarity=nlp_sim,
        mode="cascade",
    )
    assert ev.matched and ev.layer == "nlp"


@pytest.mark.asyncio
async def test_cascade_all_miss():
    async def direct_eval():
        return False, "none"

    async def heuristic_eval():
        return False, None

    async def nlp_match():
        return False

    async def nlp_sim():
        return 0.1

    ev = await evaluate_layers(
        direct_eval=direct_eval,
        heuristic_eval=heuristic_eval,
        nlp_match=nlp_match,
        nlp_similarity=nlp_sim,
        mode="cascade",
    )
    assert not ev.matched and ev.layer == "none"


@pytest.mark.asyncio
async def test_veto_mode_all_miss_matches_cascade():
    """When every layer misses, veto mode must agree with cascade (no spurious match)."""

    async def direct_eval():
        return False, "none"

    async def heuristic_eval():
        return False, None

    async def nlp_match():
        return False

    async def nlp_sim():
        return 0.05

    ev_cascade = await evaluate_layers(
        direct_eval=direct_eval,
        heuristic_eval=heuristic_eval,
        nlp_match=nlp_match,
        nlp_similarity=nlp_sim,
        mode="cascade",
    )
    ev_veto = await evaluate_layers(
        direct_eval=direct_eval,
        heuristic_eval=heuristic_eval,
        nlp_match=nlp_match,
        nlp_similarity=nlp_sim,
        mode="veto",
        veto_threshold=0.2,
    )
    assert ev_cascade.matched is False and ev_cascade.layer == "none"
    assert ev_veto.matched is False and ev_veto.layer == "none"
    assert ev_veto.notes == []


@pytest.mark.asyncio
async def test_veto_strong_direct_skips_nlp_similarity():
    calls = {"sim": 0}

    async def direct_eval():
        return True, "strong"

    async def heuristic_eval():
        raise AssertionError("heuristic should not run")

    async def nlp_match():
        raise AssertionError("nlp_match should not run")

    async def nlp_sim():
        calls["sim"] += 1
        return 0.01

    ev = await evaluate_layers(
        direct_eval=direct_eval,
        heuristic_eval=heuristic_eval,
        nlp_match=nlp_match,
        nlp_similarity=nlp_sim,
        mode="veto",
        veto_threshold=0.2,
    )
    assert ev.matched and ev.layer == "direct"
    assert calls["sim"] == 0


@pytest.mark.asyncio
async def test_veto_fuzzy_direct_low_similarity_suppressed():
    async def direct_eval():
        return True, "fuzzy"

    async def heuristic_eval():
        return False, None

    async def nlp_match():
        return False

    async def nlp_sim():
        return 0.05

    ev = await evaluate_layers(
        direct_eval=direct_eval,
        heuristic_eval=heuristic_eval,
        nlp_match=nlp_match,
        nlp_similarity=nlp_sim,
        mode="veto",
        veto_threshold=0.2,
    )
    assert not ev.matched
    assert "nlp_veto:fuzzy_direct" in ev.notes


@pytest.mark.asyncio
async def test_veto_heuristic_low_similarity_suppressed():
    async def direct_eval():
        return False, "none"

    async def heuristic_eval():
        return True, "hr"

    async def nlp_match():
        return False

    async def nlp_sim():
        return 0.05

    ev = await evaluate_layers(
        direct_eval=direct_eval,
        heuristic_eval=heuristic_eval,
        nlp_match=nlp_match,
        nlp_similarity=nlp_sim,
        mode="veto",
        veto_threshold=0.2,
    )
    assert not ev.matched
    assert "nlp_veto:heuristic" in ev.notes


@pytest.mark.asyncio
async def test_veto_fuzzy_direct_high_similarity_keeps_direct():
    async def direct_eval():
        return True, "fuzzy"

    async def heuristic_eval():
        raise AssertionError("skip")

    async def nlp_match():
        raise AssertionError("skip")

    async def nlp_sim():
        return 0.85

    ev = await evaluate_layers(
        direct_eval=direct_eval,
        heuristic_eval=heuristic_eval,
        nlp_match=nlp_match,
        nlp_similarity=nlp_sim,
        mode="veto",
        veto_threshold=0.2,
    )
    assert ev.matched and ev.layer == "direct" and ev.nlp_confirmed


@pytest.mark.asyncio
async def test_veto_after_fuzzy_suppressed_heuristic_can_win():
    async def direct_eval():
        return True, "fuzzy"

    async def heuristic_eval():
        return True, "rule-z"

    async def nlp_match():
        return False

    sim_calls = {"n": 0}

    async def nlp_sim():
        sim_calls["n"] += 1
        # First call: veto fuzzy direct; second: confirm heuristic
        return 0.05 if sim_calls["n"] == 1 else 0.9

    ev = await evaluate_layers(
        direct_eval=direct_eval,
        heuristic_eval=heuristic_eval,
        nlp_match=nlp_match,
        nlp_similarity=nlp_sim,
        mode="veto",
        veto_threshold=0.2,
    )
    assert ev.matched and ev.layer == "heuristic"


@pytest.mark.asyncio
async def test_supply_tree_uri_exact_only_direct_miss():
    async def direct_eval():
        return False, "none"

    async def heuristic_eval():
        return True, "x"

    async def nlp_match():
        return True

    async def nlp_sim():
        return 0.9

    conf, mt = await evaluate_layers_supply_tree(
        direct_eval=direct_eval,
        heuristic_eval=heuristic_eval,
        nlp_match=nlp_match,
        nlp_similarity=nlp_sim,
        partial_similarity=lambda: 0.9,
        require_direct_match=True,
        veto_enabled=False,
    )
    assert conf == 0.0 and mt == "no_match"


@pytest.mark.asyncio
async def test_supply_tree_partial_fallback():
    async def direct_eval():
        return False, "none"

    async def heuristic_eval():
        return False, None

    async def nlp_match():
        return False

    async def nlp_sim():
        return 0.1

    conf, mt = await evaluate_layers_supply_tree(
        direct_eval=direct_eval,
        heuristic_eval=heuristic_eval,
        nlp_match=nlp_match,
        nlp_similarity=nlp_sim,
        partial_similarity=lambda: 0.5,
        require_direct_match=False,
        mode="cascade",
        veto_enabled=False,
    )
    assert mt == "partial"
    assert abs(conf - 0.3) < 1e-6


@pytest.mark.asyncio
async def test_supply_tree_veto_on_strong_direct():
    async def direct_eval():
        return True, "strong"

    async def heuristic_eval():
        raise AssertionError("no")

    async def nlp_match():
        raise AssertionError("no")

    async def nlp_sim():
        return 0.01

    conf, mt = await evaluate_layers_supply_tree(
        direct_eval=direct_eval,
        heuristic_eval=heuristic_eval,
        nlp_match=nlp_match,
        nlp_similarity=nlp_sim,
        partial_similarity=lambda: 0.0,
        require_direct_match=False,
        mode="veto",
        veto_threshold=0.2,
        veto_enabled=True,
    )
    assert conf == 1.0 and mt == "direct"


@pytest.mark.asyncio
async def test_supply_tree_veto_fuzzy_low_sim_falls_through_to_nlp():
    """Fuzzy direct vetoed → heuristic miss → NLP can still win."""

    async def direct_eval():
        return True, "fuzzy"

    async def heuristic_eval():
        return False, None

    async def nlp_match():
        return True

    async def nlp_sim():
        return 0.05

    conf, mt = await evaluate_layers_supply_tree(
        direct_eval=direct_eval,
        heuristic_eval=heuristic_eval,
        nlp_match=nlp_match,
        nlp_similarity=nlp_sim,
        partial_similarity=lambda: 0.0,
        require_direct_match=False,
        mode="veto",
        veto_threshold=0.2,
        veto_enabled=True,
    )
    assert mt == "nlp"
    assert abs(conf - 0.7) < 1e-6
