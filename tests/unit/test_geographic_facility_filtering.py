"""Unit tests for geographic facility filtering (issue #172)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_facility(country=None, region=None, city=None):
    """Return a real ManufacturingFacility with the given location fields."""
    from src.core.models.okw import FacilityStatus, Location, ManufacturingFacility

    loc = Location(city=city, region=region, country=country)
    return ManufacturingFacility(
        name="Test Facility",
        location=loc,
        facility_status=FacilityStatus.ACTIVE,
    )


# ---------------------------------------------------------------------------
# _matches_filters — geographic keys (flat format)
# ---------------------------------------------------------------------------


@pytest.fixture
def matches_filters():
    from src.core.api.routes.match import _matches_filters

    return _matches_filters


def test_country_filter_matches(matches_filters):
    f = _make_facility(country="Germany")
    assert matches_filters(f, {"country": "Germany"}) is True


def test_country_filter_case_insensitive(matches_filters):
    f = _make_facility(country="germany")
    assert matches_filters(f, {"country": "GERMANY"}) is True


def test_country_filter_no_match(matches_filters):
    f = _make_facility(country="France")
    assert matches_filters(f, {"country": "Germany"}) is False


def test_region_filter_matches(matches_filters):
    f = _make_facility(region="Bavaria")
    assert matches_filters(f, {"region": "Bavaria"}) is True


def test_region_filter_no_match(matches_filters):
    f = _make_facility(region="Baden-Württemberg")
    assert matches_filters(f, {"region": "Bavaria"}) is False


def test_city_filter_matches(matches_filters):
    f = _make_facility(city="Berlin")
    assert matches_filters(f, {"city": "Berlin"}) is True


def test_multiple_geo_keys_all_must_match(matches_filters):
    f = _make_facility(country="Germany", region="Bavaria", city="Munich")
    assert matches_filters(f, {"country": "Germany", "region": "Bavaria"}) is True
    assert matches_filters(f, {"country": "Germany", "region": "Berlin"}) is False


def test_list_value_matches_any(matches_filters):
    f = _make_facility(country="France")
    assert matches_filters(f, {"country": ["Germany", "France"]}) is True


def test_list_value_no_match(matches_filters):
    f = _make_facility(country="Spain")
    assert matches_filters(f, {"country": ["Germany", "France"]}) is False


def test_missing_location_field_excluded(matches_filters):
    # facility has no location at all
    assert matches_filters({"name": "No Location"}, {"country": "Germany"}) is False


def test_empty_location_field_excluded(matches_filters):
    f = _make_facility()  # location dict present but all None
    assert matches_filters(f, {"country": "Germany"}) is False


# ---------------------------------------------------------------------------
# _get_filtered_facilities — okw_filters geographic keys applied
# ---------------------------------------------------------------------------


def _patch_for_filtered_facilities(monkeypatch, facilities):
    """Patch OKWService and local-dir resolver so _get_filtered_facilities uses only `facilities`."""
    from src.core.services import okw_service as okw_mod
    import src.core.api.routes.match as match_mod

    mock_service = AsyncMock()
    mock_service.list = AsyncMock(return_value=(facilities, len(facilities)))
    monkeypatch.setattr(
        okw_mod.OKWService, "get_instance", AsyncMock(return_value=mock_service)
    )
    monkeypatch.setattr(match_mod, "_resolve_matching_local_okw_json_dir", lambda: None)


@pytest.mark.asyncio
async def test_get_filtered_facilities_applies_country_filter(monkeypatch):
    from src.core.api.models.match.request import MatchRequest
    from src.core.api.routes.match import _get_filtered_facilities

    german = _make_facility(country="Germany")
    french = _make_facility(country="France")
    _patch_for_filtered_facilities(monkeypatch, [german, french])

    req = MatchRequest.model_construct(
        okw_facilities=None,
        access_type=None,
        facility_status=None,
        location=None,
        okw_filters={"country": "Germany"},
    )

    facilities = await _get_filtered_facilities(
        storage_service=None, request=req, request_id="test", domain="manufacturing"
    )
    assert len(facilities) == 1


@pytest.mark.asyncio
async def test_get_filtered_facilities_applies_region_filter(monkeypatch):
    from src.core.api.models.match.request import MatchRequest
    from src.core.api.routes.match import _get_filtered_facilities

    bavarian = _make_facility(country="Germany", region="Bavaria")
    berlin = _make_facility(country="Germany", region="Berlin")
    _patch_for_filtered_facilities(monkeypatch, [bavarian, berlin])

    req = MatchRequest.model_construct(
        okw_facilities=None,
        access_type=None,
        facility_status=None,
        location=None,
        okw_filters={"region": "Bavaria"},
    )

    facilities = await _get_filtered_facilities(
        storage_service=None, request=req, request_id="test", domain="manufacturing"
    )
    assert len(facilities) == 1


@pytest.mark.asyncio
async def test_get_filtered_facilities_list_country_filter(monkeypatch):
    from src.core.api.models.match.request import MatchRequest
    from src.core.api.routes.match import _get_filtered_facilities

    german = _make_facility(country="Germany")
    french = _make_facility(country="France")
    spanish = _make_facility(country="Spain")
    _patch_for_filtered_facilities(monkeypatch, [german, french, spanish])

    req = MatchRequest.model_construct(
        okw_facilities=None,
        access_type=None,
        facility_status=None,
        location=None,
        okw_filters={"country": ["Germany", "France"]},
    )

    facilities = await _get_filtered_facilities(
        storage_service=None, request=req, request_id="test", domain="manufacturing"
    )
    assert len(facilities) == 2


@pytest.mark.asyncio
async def test_get_filtered_facilities_no_geo_filters_passes_all(monkeypatch):
    from src.core.api.models.match.request import MatchRequest
    from src.core.api.routes.match import _get_filtered_facilities

    f1 = _make_facility(country="Germany")
    f2 = _make_facility(country="France")
    _patch_for_filtered_facilities(monkeypatch, [f1, f2])

    req = MatchRequest.model_construct(
        okw_facilities=None,
        access_type=None,
        facility_status=None,
        location=None,
        okw_filters={},
    )

    facilities = await _get_filtered_facilities(
        storage_service=None, request=req, request_id="test", domain="manufacturing"
    )
    assert len(facilities) == 2


# ---------------------------------------------------------------------------
# CLI _parse_match_filters — country/region populate okw_filters
# ---------------------------------------------------------------------------


def test_parse_match_filters_country_populates_okw_filters():
    from src.cli.match import _parse_match_filters

    result = _parse_match_filters(
        access_type=None,
        facility_status=None,
        location=None,
        country="Germany",
        region=None,
        capabilities=None,
        materials=None,
        min_confidence=0.1,
        max_results=10,
    )
    assert result["okw_filters"] == {"country": "Germany"}


def test_parse_match_filters_region_populates_okw_filters():
    from src.cli.match import _parse_match_filters

    result = _parse_match_filters(
        access_type=None,
        facility_status=None,
        location=None,
        country=None,
        region="Bavaria",
        capabilities=None,
        materials=None,
        min_confidence=0.1,
        max_results=10,
    )
    assert result["okw_filters"] == {"region": "Bavaria"}


def test_parse_match_filters_country_and_region_combined():
    from src.cli.match import _parse_match_filters

    result = _parse_match_filters(
        access_type=None,
        facility_status=None,
        location=None,
        country="Germany",
        region="Bavaria",
        capabilities=None,
        materials=None,
        min_confidence=0.1,
        max_results=10,
    )
    assert result["okw_filters"] == {"country": "Germany", "region": "Bavaria"}


def test_parse_match_filters_no_geo_omits_okw_filters():
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
    )
    assert "okw_filters" not in result
