"""A saved supply tree belongs to whoever ran the match, and to nobody else.

The Solutions browse was removed in df639dd because it listed every visitor's
searches: solutions are written to one shared prefix, and
``GET /api/supply-tree/solutions`` took no user dependency and applied no owner
filter, so any caller received the whole store. The commit deferred the rebuild
— "the list endpoint is left server-side for user-scoped history post-auth".

This is that scoping. It follows the shape fcb85ad established for OKH/OKW
reads: ``get_viewer`` resolves the caller without ever rejecting them, and the
filter lives in the service so it runs before pagination rather than after.

The legacy case is the one that matters most. Solutions already in storage
carry no owner, and treating an absent owner as "public" would keep the leak
open for exactly the rows that caused it — so an unowned solution is listed for
nobody.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.services.storage_service import StorageService  # noqa: E402
from src.core.storage.constants import (  # noqa: E402
    SUPPLY_TREE_SOLUTIONS_METADATA_PREFIX,
)

ALICE = "acct-alice"
BOB = "acct-bob"

ALICE_SOLUTION = UUID("11111111-1111-4111-8111-111111111111")
BOB_SOLUTION = UUID("22222222-2222-4222-8222-222222222222")
LEGACY_SOLUTION = UUID("33333333-3333-4333-8333-333333333333")


class _InMemoryManager:
    """Just enough object store to exercise the listing loop."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def put_object(self, key, data, content_type=None, metadata=None):
        self._objects[key] = data

    async def get_object(self, key):
        return self._objects[key]

    async def list_objects(self, prefix=None):
        for key, data in list(self._objects.items()):
            if prefix is None or key.startswith(prefix):
                yield {"key": key, "data": data, "last_modified": None}


def _metadata(solution_id: UUID, created_by: str | None) -> dict:
    """A sidecar metadata row. ``created_by=None`` is a pre-scoping solution."""
    now = datetime.now().isoformat()
    row = {
        "id": str(solution_id),
        "okh_id": "okh-1",
        "okh_title": f"Design {solution_id.hex[:4]}",
        "facility_name": "Somewhere",
        "matching_mode": "single-level",
        "tree_count": 1,
        "component_count": 1,
        "facility_count": 1,
        "score": 0.9,
        "created_at": now,
        "updated_at": now,
        "expires_at": now,
        "ttl_days": 30,
        "tags": [],
    }
    if created_by is not None:
        row["created_by"] = created_by
    return row


def _service() -> StorageService:
    service = StorageService.__new__(StorageService)
    service._configured = True
    service.manager = _InMemoryManager()
    for solution_id, owner in (
        (ALICE_SOLUTION, ALICE),
        (BOB_SOLUTION, BOB),
        (LEGACY_SOLUTION, None),
    ):
        key = f"{SUPPLY_TREE_SOLUTIONS_METADATA_PREFIX}/{solution_id}.json"
        service.manager._objects[key] = json.dumps(
            _metadata(solution_id, owner)
        ).encode("utf-8")
    return service


async def _ids_for(service: StorageService, created_by: str | None) -> set[str]:
    rows = await service.list_supply_tree_solutions(created_by=created_by)
    return {row["id"] for row in rows}


@pytest.mark.asyncio
@pytest.mark.contract
async def test_list_returns_only_the_callers_own_solutions() -> None:
    service = _service()
    assert await _ids_for(service, ALICE) == {str(ALICE_SOLUTION)}
    assert await _ids_for(service, BOB) == {str(BOB_SOLUTION)}


@pytest.mark.asyncio
@pytest.mark.contract
async def test_anonymous_caller_gets_nothing_rather_than_everything() -> None:
    """The original defect, stated directly."""
    service = _service()
    assert await _ids_for(service, None) == set()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_ownerless_legacy_solutions_are_listed_for_nobody() -> None:
    """Fail closed: an absent owner is not a wildcard."""
    service = _service()
    for viewer in (ALICE, BOB, None):
        assert str(LEGACY_SOLUTION) not in await _ids_for(service, viewer)


@pytest.mark.asyncio
@pytest.mark.contract
async def test_route_scopes_an_anonymous_request_to_an_empty_list() -> None:
    """End to end through the router, with no credential supplied."""
    from src.core.api.routes.supply_tree import get_storage_service
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)

    service = MagicMock()
    service.list_supply_tree_solutions = AsyncMock(return_value=[])
    api_v1.dependency_overrides[get_storage_service] = lambda: service
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get("/v1/api/supply-tree/solutions")
        assert resp.status_code == 200, resp.text
        # The route must ask the service for *this caller's* rows. Anonymous
        # resolves to None, and the service treats None as "no owner matches".
        service.list_supply_tree_solutions.assert_awaited()
        assert (
            service.list_supply_tree_solutions.await_args.kwargs["created_by"] is None
        )
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_save_records_the_caller_as_owner() -> None:
    """Attribution has to happen on the write, or the filter has nothing to read."""
    from src.core.models.supply_trees import SupplyTreeSolution

    service = StorageService.__new__(StorageService)
    service._configured = True
    service.manager = _InMemoryManager()

    solution = SupplyTreeSolution.__new__(SupplyTreeSolution)
    solution.all_trees = []
    solution.component_mapping = None
    solution.score = 1.0
    solution.metadata = {"okh_id": "okh-1"}
    solution.to_dict = lambda: {"all_trees": []}

    solution_id = await service.save_supply_tree_solution(solution, created_by=ALICE)

    key = f"{SUPPLY_TREE_SOLUTIONS_METADATA_PREFIX}/{solution_id}.json"
    stored = json.loads(service.manager._objects[key].decode("utf-8"))
    assert stored["created_by"] == ALICE
