"""Unit tests for compatible_manifest_ids field and salvage_match expansion — GAP-8."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.core.models.asset import AssetRecord, ComponentCondition, ComponentState

# ---------------------------------------------------------------------------
# OKHManifest field
# ---------------------------------------------------------------------------


def _minimal_manifest_dict(**kwargs):
    base = {
        "title": "Test Device",
        "version": "1.0.0",
        "license": {"hardware": "CERN-OHL-S-2.0"},
        "licensor": "Test Suite",
        "documentation_language": "en",
        "function": "test",
    }
    base.update(kwargs)
    return base


def test_manifest_defaults_compatible_manifest_ids_empty():
    from src.core.models.okh import OKHManifest

    m = OKHManifest.from_dict(_minimal_manifest_dict())
    assert m.compatible_manifest_ids == []


def test_manifest_from_dict_parses_compatible_manifest_ids():
    from src.core.models.okh import OKHManifest

    ids = [str(uuid4()), str(uuid4())]
    m = OKHManifest.from_dict(_minimal_manifest_dict(compatible_manifest_ids=ids))
    assert m.compatible_manifest_ids == ids


def test_manifest_to_dict_includes_compatible_manifest_ids():
    from src.core.models.okh import OKHManifest

    ids = [str(uuid4())]
    m = OKHManifest.from_dict(_minimal_manifest_dict(compatible_manifest_ids=ids))
    d = m.to_dict()
    assert d["compatible_manifest_ids"] == ids


def test_manifest_round_trip_empty_list():
    from src.core.models.okh import OKHManifest

    m = OKHManifest.from_dict(_minimal_manifest_dict())
    d = m.to_dict()
    m2 = OKHManifest.from_dict(d)
    assert m2.compatible_manifest_ids == []


def test_manifest_round_trip_with_ids():
    from src.core.models.okh import OKHManifest

    ids = [str(uuid4()), str(uuid4())]
    m = OKHManifest.from_dict(_minimal_manifest_dict(compatible_manifest_ids=ids))
    d = m.to_dict()
    m2 = OKHManifest.from_dict(d)
    assert m2.compatible_manifest_ids == ids


def test_manifest_from_dict_migration_safe_no_field():
    """Existing manifests without compatible_manifest_ids deserialise safely."""
    from src.core.models.okh import OKHManifest

    m = OKHManifest.from_dict(_minimal_manifest_dict())
    assert m.compatible_manifest_ids == []


# ---------------------------------------------------------------------------
# AssetService.salvage_match — manifest expansion
# ---------------------------------------------------------------------------


def _record_with_harvest_viable(manifest_id: str) -> AssetRecord:
    record = AssetRecord(manifest_id=manifest_id, asset_tag=f"TAG-{manifest_id[:4]}")
    cs = ComponentState(
        component_name="Pump",
        condition=ComponentCondition.INTACT,
        harvest_viable=True,
    )
    record.component_states = [cs]
    return record


def _mock_manifest(manifest_id: str, compatible_ids=None):
    m = MagicMock()
    m.id = manifest_id
    m.compatible_manifest_ids = compatible_ids or []
    m.components = []
    return m


def _patch_okh_service(fake_get_coro):
    """Patch OKHService.get_instance at its source module."""
    from src.core.services import okh_service as _okh_mod

    okh_svc_mock = MagicMock()
    okh_svc_mock.get = fake_get_coro
    return patch.object(
        _okh_mod.OKHService,
        "get_instance",
        new=AsyncMock(return_value=okh_svc_mock),
    )


@pytest.mark.asyncio
async def test_salvage_match_expands_to_compatible_manifests():
    """When manifest_id is set and has compatible_manifest_ids, matches from those manifests appear."""
    from src.core.services.asset_service import AssetService

    primary_id = str(uuid4())
    compat_id = str(uuid4())

    record_primary = _record_with_harvest_viable(primary_id)
    record_compat = _record_with_harvest_viable(compat_id)

    svc = AssetService.__new__(AssetService)

    primary_manifest = _mock_manifest(primary_id, compatible_ids=[compat_id])
    compat_manifest = _mock_manifest(compat_id)

    async def fake_get(mid):
        return primary_manifest if str(mid) == primary_id else compat_manifest

    with (
        patch.object(svc, "ensure_initialized", new=AsyncMock()),
        patch.object(
            svc, "list", new=AsyncMock(return_value=[record_primary, record_compat])
        ),
        _patch_okh_service(AsyncMock(side_effect=fake_get)),
    ):
        result = await svc.salvage_match(component_name="Pump", manifest_id=primary_id)

    asset_ids = {m.asset_id for m in result.matches}
    assert str(record_primary.id) in asset_ids, "Primary manifest match missing"
    assert str(record_compat.id) in asset_ids, "Compatible manifest match missing"


@pytest.mark.asyncio
async def test_salvage_match_no_expansion_without_manifest_id():
    """Without manifest_id, all assets are searched regardless of compatible_manifest_ids."""
    from src.core.services.asset_service import AssetService

    id_a = str(uuid4())
    id_b = str(uuid4())
    records = [_record_with_harvest_viable(id_a), _record_with_harvest_viable(id_b)]

    svc = AssetService.__new__(AssetService)

    with (
        patch.object(svc, "ensure_initialized", new=AsyncMock()),
        patch.object(svc, "list", new=AsyncMock(return_value=records)),
        _patch_okh_service(AsyncMock(return_value=_mock_manifest(id_a))),
    ):
        result = await svc.salvage_match(component_name="Pump")

    assert result.total == 2


@pytest.mark.asyncio
async def test_salvage_match_scopes_to_single_manifest_when_no_compat():
    """When manifest has no compatible_manifest_ids, search is scoped to exactly that manifest."""
    from src.core.services.asset_service import AssetService

    target_id = str(uuid4())
    other_id = str(uuid4())

    record_target = _record_with_harvest_viable(target_id)
    record_other = _record_with_harvest_viable(other_id)

    svc = AssetService.__new__(AssetService)

    with (
        patch.object(svc, "ensure_initialized", new=AsyncMock()),
        patch.object(
            svc,
            "list",
            new=AsyncMock(return_value=[record_target, record_other]),
        ),
        _patch_okh_service(
            AsyncMock(return_value=_mock_manifest(target_id, compatible_ids=[]))
        ),
    ):
        result = await svc.salvage_match(component_name="Pump", manifest_id=target_id)

    assert result.total == 1
    assert result.matches[0].asset_id == str(record_target.id)
