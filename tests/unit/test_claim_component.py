"""Unit tests for ComponentState claim fields and AssetService.claim_component — GAP-7."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.core.models.asset import ComponentCondition, ComponentState

# ---------------------------------------------------------------------------
# ComponentState.is_claimed
# ---------------------------------------------------------------------------


def test_unclaimed_state_is_not_claimed():
    cs = ComponentState(component_name="Pump")
    assert cs.is_claimed is False


def test_claimed_by_without_claimed_at_is_not_claimed():
    cs = ComponentState(component_name="Pump", claimed_by="coord-1")
    assert cs.is_claimed is False


def test_fresh_claim_is_claimed():
    cs = ComponentState(
        component_name="Pump",
        claimed_by="coord-1",
        claimed_at=datetime.now(timezone.utc),
    )
    assert cs.is_claimed is True


def test_expired_claim_is_not_claimed():
    old = datetime.now(timezone.utc) - timedelta(hours=49)
    cs = ComponentState(
        component_name="Pump",
        claimed_by="coord-1",
        claimed_at=old,
    )
    assert cs.is_claimed is False


def test_claim_at_exactly_48h_is_expired():
    exactly_48h = datetime.now(timezone.utc) - timedelta(hours=48)
    cs = ComponentState(
        component_name="Pump",
        claimed_by="coord-1",
        claimed_at=exactly_48h,
    )
    assert cs.is_claimed is False


def test_claim_round_trip_through_dict():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    cs = ComponentState(
        component_name="Pump",
        claimed_by="coord-1",
        claimed_at=now,
    )
    d = cs.to_dict()
    assert d["claimed_by"] == "coord-1"
    assert d["claimed_at"] == now.isoformat()

    restored = ComponentState.from_dict(d)
    assert restored.claimed_by == "coord-1"
    assert restored.is_claimed is True


def test_unclaimed_round_trip_through_dict():
    cs = ComponentState(component_name="Pump")
    d = cs.to_dict()
    assert d["claimed_by"] is None
    assert d["claimed_at"] is None

    restored = ComponentState.from_dict(d)
    assert restored.claimed_by is None
    assert restored.is_claimed is False


def test_from_dict_migration_safe_missing_claim_fields():
    """Existing stored records without claim fields parse safely."""
    cs = ComponentState.from_dict({"component_name": "Pump", "condition": "intact"})
    assert cs.claimed_by is None
    assert cs.claimed_at is None
    assert cs.is_claimed is False


# ---------------------------------------------------------------------------
# AssetService.claim_component (via mocked storage)
# ---------------------------------------------------------------------------


def _make_record_with_component(component_name: str, harvest_viable: bool = True):
    from src.core.models.asset import AssetRecord

    record = AssetRecord(
        manifest_id="manifest-uuid",
        asset_tag="TAG-001",
    )
    cs = ComponentState(
        component_name=component_name,
        condition=ComponentCondition.INTACT,
        harvest_viable=harvest_viable,
    )
    record.component_states = [cs]
    return record


@pytest.mark.asyncio
async def test_claim_component_sets_claimed_by_and_at():
    from src.core.services.asset_service import AssetService

    svc = AssetService.__new__(AssetService)
    record = _make_record_with_component("Blood pump")

    with (
        patch.object(svc, "ensure_initialized", new=AsyncMock()),
        patch.object(svc, "get", new=AsyncMock(return_value=record)),
        patch.object(svc, "update", new=AsyncMock(return_value=record)),
    ):
        from uuid import uuid4

        cs = await svc.claim_component(
            asset_id=uuid4(),
            component_name="Blood pump",
            claimed_by="coord-1",
        )

    assert cs.claimed_by == "coord-1"
    assert cs.claimed_at is not None
    assert cs.is_claimed is True


@pytest.mark.asyncio
async def test_claim_component_raises_on_already_claimed():
    from src.core.services.asset_service import AssetService

    svc = AssetService.__new__(AssetService)
    record = _make_record_with_component("Blood pump")
    record.component_states[0].claimed_by = "coord-1"
    record.component_states[0].claimed_at = datetime.now(timezone.utc)

    with (
        patch.object(svc, "ensure_initialized", new=AsyncMock()),
        patch.object(svc, "get", new=AsyncMock(return_value=record)),
    ):
        from uuid import uuid4

        with pytest.raises(ValueError, match="already claimed"):
            await svc.claim_component(
                asset_id=uuid4(),
                component_name="Blood pump",
                claimed_by="coord-2",
            )


@pytest.mark.asyncio
async def test_claim_component_raises_on_unknown_asset():
    from src.core.services.asset_service import AssetService

    svc = AssetService.__new__(AssetService)

    with (
        patch.object(svc, "ensure_initialized", new=AsyncMock()),
        patch.object(svc, "get", new=AsyncMock(return_value=None)),
    ):
        from uuid import uuid4

        with pytest.raises(KeyError):
            await svc.claim_component(
                asset_id=uuid4(),
                component_name="Blood pump",
                claimed_by="coord-1",
            )


@pytest.mark.asyncio
async def test_claim_component_raises_on_unknown_component():
    from src.core.services.asset_service import AssetService

    svc = AssetService.__new__(AssetService)
    record = _make_record_with_component("Blood pump")

    with (
        patch.object(svc, "ensure_initialized", new=AsyncMock()),
        patch.object(svc, "get", new=AsyncMock(return_value=record)),
    ):
        from uuid import uuid4

        with pytest.raises(KeyError):
            await svc.claim_component(
                asset_id=uuid4(),
                component_name="Nonexistent Part",
                claimed_by="coord-1",
            )


@pytest.mark.asyncio
async def test_expired_claim_can_be_reclaimed():
    from src.core.services.asset_service import AssetService

    svc = AssetService.__new__(AssetService)
    record = _make_record_with_component("Blood pump")
    record.component_states[0].claimed_by = "coord-old"
    record.component_states[0].claimed_at = datetime.now(timezone.utc) - timedelta(
        hours=49
    )

    with (
        patch.object(svc, "ensure_initialized", new=AsyncMock()),
        patch.object(svc, "get", new=AsyncMock(return_value=record)),
        patch.object(svc, "update", new=AsyncMock(return_value=record)),
    ):
        from uuid import uuid4

        cs = await svc.claim_component(
            asset_id=uuid4(),
            component_name="Blood pump",
            claimed_by="coord-new",
        )

    assert cs.claimed_by == "coord-new"
