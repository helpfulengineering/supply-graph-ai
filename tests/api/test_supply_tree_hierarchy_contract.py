"""Contract: GET /v1/api/supply-tree/solution/{id}/hierarchy is shape-frozen.

This route returned a bare ``dict``, so ``openapi-typescript`` generated no
response type for it and the frontend hand-wrote one. The guess was wrong —
``root_components`` was typed ``string[]`` against objects — and rendering it
threw React #31 in front of a user (#369).

Adding a ``response_model`` is what lets codegen type the route. But FastAPI's
``response_model`` *filters*: any field the model does not declare is silently
dropped from the JSON. A model written by reading the route can therefore
delete a field a client reads, which is the same class of bug the model is
meant to close.

So the payload is frozen against a golden capture taken from the route BEFORE
the model existed. The model is correct exactly when this test passes: same
keys, same values, nothing filtered.

To change the contract deliberately:
    BLESS_HIERARCHY_CONTRACT=1 .venv/bin/python -m pytest \
        tests/api/test_supply_tree_hierarchy_contract.py
and commit the regenerated golden with the reason in the message.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from src.core.models.supply_trees import SupplyTree, SupplyTreeSolution
from src.core.services.storage_service import StorageService
from src.core.storage.base import StorageConfig

GOLDEN = Path(__file__).parent / "golden" / "supply_tree_hierarchy.json"

# Fixed so the capture is byte-stable across runs: the payload embeds tree ids
# and the solution id, and random UUIDs would make every run a diff.
ROOT_TREE_ID = "11111111-1111-1111-1111-111111111111"
CHILD_TREE_ID = "22222222-2222-2222-2222-222222222222"


def _solution() -> SupplyTreeSolution:
    """A solution with a parent and a child, so every payload key is non-empty.

    A single-tree solution leaves ``children`` empty everywhere and would let a
    model that drops nested nodes pass.
    """
    root = SupplyTree(
        id=ROOT_TREE_ID,
        facility_name="FabLab Drome",
        okh_reference="okh-vent",
        okw_reference="okw-drome",
        confidence_score=0.95,
        match_type="direct",
        component_id="frame",
        component_name="Frame",
        depth=0,
        production_stage="fabrication",
    )
    child = SupplyTree(
        id=CHILD_TREE_ID,
        facility_name="FabLab Drome",
        okh_reference="okh-vent",
        okw_reference="okw-drome",
        confidence_score=0.80,
        match_type="direct",
        component_id="pump",
        component_name="Pump assembly",
        depth=1,
        production_stage="assembly",
        parent_tree_id=ROOT_TREE_ID,
    )
    return SupplyTreeSolution(all_trees=[root, child], score=0.9, metadata={})


def _app():
    """The mounted app plus the sub-app that owns the dependency overrides."""
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


def _stub_timestamps(node):
    """Replace per-run clock values wherever they appear in the payload.

    ``creation_time`` is stamped on every serialised tree, so without this the
    test would fail on a clock tick rather than on a contract change. Recursive
    because the trees are nested inside ``component_details``.
    """
    if isinstance(node, dict):
        return {
            k: ("<timestamp>" if k == "creation_time" else _stub_timestamps(v))
            for k, v in node.items()
        }
    if isinstance(node, list):
        return [_stub_timestamps(v) for v in node]
    return node


def _normalise(payload: dict) -> dict:
    """Drop the envelope fields that legitimately differ every run.

    ``timestamp``, ``request_id`` and the processing metrics are per-request by
    design; freezing them would make the test fail on a clock tick rather than
    on a contract change.
    """
    body = _stub_timestamps(payload)
    body.pop("timestamp", None)
    body.pop("request_id", None)
    body["metadata"] = {
        k: v
        for k, v in (body.get("metadata") or {}).items()
        if k not in {"processing_time", "timestamp"}
    }
    return body


@pytest.mark.asyncio
@pytest.mark.contract
async def test_hierarchy_payload_is_field_identical_to_the_golden(tmp_path):
    storage = StorageService()
    await storage.configure(StorageConfig(provider="local", bucket_name=str(tmp_path)))
    assert storage._configured

    solution_id = await storage.save_supply_tree_solution(
        _solution(), ttl_days=1, tags=["hierarchy-contract"]
    )

    app, api_v1 = _app()
    from src.core.api.routes import supply_tree as route_module

    api_v1.dependency_overrides[route_module.get_storage_service] = lambda: storage

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/v1/api/supply-tree/solution/{solution_id}/hierarchy"
        )

    assert response.status_code == 200, response.text
    body = _normalise(response.json())
    # The solution id is generated per run; the golden holds a placeholder.
    body = json.loads(json.dumps(body).replace(str(solution_id), "<solution-id>"))

    if os.getenv("BLESS_HIERARCHY_CONTRACT"):
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
        pytest.skip("golden re-blessed")

    assert GOLDEN.exists(), (
        f"No golden at {GOLDEN}. Capture one with "
        "BLESS_HIERARCHY_CONTRACT=1 before adding a response_model."
    )
    expected = json.loads(GOLDEN.read_text())
    assert body == expected, (
        "The hierarchy payload changed. If a response_model was just added, it "
        "is filtering a field the route used to return."
    )
