"""Unit tests for the okw_ids facility-subset filter (web-ui review #4).

A caller can pre-select which facilities to match against; the match request's
``okw_ids`` narrows the candidate pool to those IDs before matching, and the CLI
exposes the same control through repeatable ``--okw-id`` options.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _make_facility(facility_id: str):
    from src.core.models.okw import FacilityStatus, Location, ManufacturingFacility

    return ManufacturingFacility(
        name=f"Facility {facility_id}",
        location=Location(city="Austin"),
        facility_status=FacilityStatus.ACTIVE,
        id=facility_id,
    )


def _patch_for_filtered_facilities(monkeypatch, facilities):
    """Patch OKWService + local-dir resolver so the loader returns only `facilities`."""
    from src.core.services import okw_service as okw_mod
    import src.core.api.routes.match as match_mod

    mock_service = AsyncMock()
    mock_service.list = AsyncMock(return_value=(facilities, len(facilities)))
    monkeypatch.setattr(
        okw_mod.OKWService, "get_instance", AsyncMock(return_value=mock_service)
    )
    monkeypatch.setattr(match_mod, "_resolve_matching_local_okw_json_dir", lambda: None)


def _request(**overrides):
    from src.core.api.models.match.request import MatchRequest

    base = dict(
        okw_facilities=None,
        access_type=None,
        facility_status=None,
        location=None,
        okw_filters={},
        okw_ids=None,
    )
    base.update(overrides)
    return MatchRequest.model_construct(**base)


# ---------------------------------------------------------------------------
# _get_filtered_facilities — okw_ids subset
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_okw_ids_restricts_pool_to_subset(monkeypatch):
    from src.core.api.routes.match import _get_filtered_facilities

    a, b, c = _make_facility("okw-a"), _make_facility("okw-b"), _make_facility("okw-c")
    _patch_for_filtered_facilities(monkeypatch, [a, b, c])

    facilities = await _get_filtered_facilities(
        storage_service=None,
        request=_request(okw_ids=["okw-a", "okw-c"]),
        request_id="test",
        domain="manufacturing",
    )

    assert {str(f.id) for f in facilities} == {"okw-a", "okw-c"}


@pytest.mark.asyncio
async def test_empty_okw_ids_passes_all(monkeypatch):
    from src.core.api.routes.match import _get_filtered_facilities

    a, b = _make_facility("okw-a"), _make_facility("okw-b")
    _patch_for_filtered_facilities(monkeypatch, [a, b])

    facilities = await _get_filtered_facilities(
        storage_service=None,
        request=_request(okw_ids=[]),
        request_id="test",
        domain="manufacturing",
    )

    assert len(facilities) == 2


@pytest.mark.asyncio
async def test_okw_ids_unknown_id_yields_empty_pool(monkeypatch):
    from src.core.api.routes.match import _get_filtered_facilities

    a = _make_facility("okw-a")
    _patch_for_filtered_facilities(monkeypatch, [a])

    facilities = await _get_filtered_facilities(
        storage_service=None,
        request=_request(okw_ids=["does-not-exist"]),
        request_id="test",
        domain="manufacturing",
    )

    assert facilities == []


# ---------------------------------------------------------------------------
# CLI _parse_match_filters — okw_ids
# ---------------------------------------------------------------------------


def test_parse_match_filters_populates_okw_ids():
    from src.cli.match import _parse_match_filters

    result = _parse_match_filters(
        access_type=None,
        facility_status=None,
        location=None,
        country=None,
        region=None,
        capabilities=None,
        materials=None,
        min_confidence=0.1,
        max_results=10,
        okw_ids=("okw-a", "okw-b"),
    )
    assert result["okw_ids"] == ["okw-a", "okw-b"]


def test_parse_match_filters_omits_okw_ids_when_empty():
    from src.cli.match import _parse_match_filters

    result = _parse_match_filters(
        access_type=None,
        facility_status=None,
        location=None,
        country=None,
        region=None,
        capabilities=None,
        materials=None,
        min_confidence=0.1,
        max_results=10,
        okw_ids=(),
    )
    assert "okw_ids" not in result
