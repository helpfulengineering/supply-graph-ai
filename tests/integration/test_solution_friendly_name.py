"""
Saved supply-tree solutions must carry a human-readable identity — the design
title and primary facility — in their metadata, so the UI lists them by name
rather than a bare UUID (web-ui review note #2).

Regression guard for the fix: the match auto-save now records okh_title +
facility_name, and storage persists/returns them through save -> list.

The test builds its own local-backed StorageService rather than reusing the
process-wide singleton, so it stays hermetic regardless of what provider an
earlier test left configured (StorageService keeps its own `_instance`, which
the integration `client` fixture does not reset).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.core.models.supply_trees import SupplyTree, SupplyTreeSolution
from src.core.services.storage_service import StorageService
from src.core.storage.base import StorageConfig


@pytest.mark.integration
@pytest.mark.asyncio
async def test_saved_solution_lists_with_design_title_and_facility(tmp_path):
    storage = StorageService()
    await storage.configure(StorageConfig(provider="local", bucket_name=str(tmp_path)))
    assert storage._configured, "local storage provider should configure"

    tree = SupplyTree(
        facility_name="FabLab Drome",
        okh_reference="okh-vent",
        okw_reference=str(uuid4()),
        confidence_score=0.95,
        match_type="direct",
        metadata={"okh_title": "Open Ventilator", "facility_name": "FabLab Drome"},
    )
    solution = SupplyTreeSolution(
        all_trees=[tree],
        score=0.95,
        metadata={
            "okh_id": "okh-vent",
            "okh_title": "Open Ventilator",
            "facility_name": "FabLab Drome",
            "matching_mode": "single-level",
        },
    )

    solution_id = await storage.save_supply_tree_solution(
        solution, ttl_days=1, tags=["friendly-name-test"]
    )
    try:
        solutions = await storage.list_supply_tree_solutions(limit=200)
        saved = next(s for s in solutions if s["id"] == str(solution_id))
        assert saved["okh_title"] == "Open Ventilator"
        assert saved["facility_name"] == "FabLab Drome"
    finally:
        await storage.delete_supply_tree_solution(solution_id)
