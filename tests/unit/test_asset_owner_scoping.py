"""An asset is readable by whoever created it, and by nobody else (#493).

Every asset read was anonymous and unscoped: `GET /v1/api/asset` served every
asset on the node to any caller — asset tag, location, triage notes, who claimed
which component. #492 closed the writes on this surface; the reads were never
the part anyone chose to make public.

Assets deliberately have **no visibility plane**: there is no way to share one,
so the rule is ownership alone. `visible_to` is still the call made, with
``None`` for the level, so adding a level later needs no change at the filter.

The `viewer=None` cases are not an oversight — that is the unscoped path for
trusted internal callers (the CLI), and it doubles as the calibration for every
other case here: it proves the fixture actually holds records, so an empty
result elsewhere means scoping rather than an empty store.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.core.models.visibility import ANONYMOUS_SCOPE, ViewerScope
from src.core.services.asset_service import AssetService

pytestmark = pytest.mark.unit

ALICE = ViewerScope(account_id="acct-alice")
BOB = ViewerScope(account_id="acct-bob")

ALICE_ASSET = str(uuid4())
BOB_ASSET = str(uuid4())
ORPHAN_ASSET = str(uuid4())


def _stored(asset_id: str, account: str | None) -> dict:
    row = {
        "id": asset_id,
        "manifest_id": str(uuid4()),
        "asset_tag": f"TAG-{asset_id[:4]}",
        "location": "ICU Bay 3",
        "status": "active",
        "component_states": [],
    }
    if account is not None:
        row["ohm_created_by"] = account
    return row


def _service() -> AssetService:
    """An AssetService over three stored assets: Alice's, Bob's, and an orphan."""
    rows = {
        f"asset/{ALICE_ASSET}.json": _stored(ALICE_ASSET, "acct-alice"),
        f"asset/{BOB_ASSET}.json": _stored(BOB_ASSET, "acct-bob"),
        f"asset/{ORPHAN_ASSET}.json": _stored(ORPHAN_ASSET, None),
    }

    async def get_object(key):
        return json.dumps(rows[key]).encode()

    service = AssetService.__new__(AssetService)
    service.storage = SimpleNamespace(manager=SimpleNamespace(get_object=get_object))
    return service


def _discovery():
    files = [
        SimpleNamespace(key=f"asset/{ALICE_ASSET}.json"),
        SimpleNamespace(key=f"asset/{BOB_ASSET}.json"),
        SimpleNamespace(key=f"asset/{ORPHAN_ASSET}.json"),
    ]
    return patch(
        "src.core.services.asset_service.SmartFileDiscovery",
        return_value=SimpleNamespace(discover_files=AsyncMock(return_value=files)),
    )


@asynccontextmanager
async def _no_metrics(*_args, **_kwargs):
    """`get()` wraps itself in track_request; `list()` does not."""
    yield


async def _ids(viewer) -> set[str]:
    service = _service()
    with patch.object(service, "ensure_initialized", new=AsyncMock()), _discovery():
        return {str(r.id) for r in await service.list(viewer=viewer)}


@pytest.mark.asyncio
async def test_unscoped_list_sees_everything():
    """The trusted internal path — and the calibration for every case below."""
    assert await _ids(None) == {ALICE_ASSET, BOB_ASSET, ORPHAN_ASSET}


@pytest.mark.asyncio
async def test_a_viewer_sees_only_their_own():
    assert await _ids(ALICE) == {ALICE_ASSET}
    assert await _ids(BOB) == {BOB_ASSET}


@pytest.mark.asyncio
async def test_anonymous_sees_nothing():
    """The defect, stated directly."""
    assert await _ids(ANONYMOUS_SCOPE) == set()


@pytest.mark.asyncio
async def test_an_asset_with_no_owner_is_readable_by_nobody():
    """No owner, no reader — and it is not a wildcard either."""
    for viewer in (ALICE, BOB, ANONYMOUS_SCOPE):
        assert ORPHAN_ASSET not in await _ids(viewer)


@pytest.mark.asyncio
async def test_get_404s_for_another_owner():
    service = _service()
    with (
        patch.object(service, "ensure_initialized", new=AsyncMock()),
        patch.object(service, "track_request", new=_no_metrics),
        _discovery(),
    ):
        assert await service.get(ALICE_ASSET, viewer=ALICE) is not None
        assert await service.get(ALICE_ASSET, viewer=BOB) is None
        assert await service.get(ALICE_ASSET, viewer=ANONYMOUS_SCOPE) is None
