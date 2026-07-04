"""Unit tests for OKW geographic coordinates (dashboard map, review #1).

The OKW standard stores GPS coordinates as a single decimal-degrees string.
`parse_decimal_degrees` / `Location.coordinates()` is the one typed accessor for
it, and `Location.to_dict()` surfaces a structured `{lat, lon}` for the web map.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.core.models.okw import (  # noqa: E402
    Coordinates,
    Location,
    parse_decimal_degrees,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("42.3588, -71.0578", Coordinates(42.3588, -71.0578)),
        ("  42.0 ,  -71.0 ", Coordinates(42.0, -71.0)),  # tolerant of whitespace
        ("0, 0", Coordinates(0.0, 0.0)),
        ("-33.8688, 151.2093", Coordinates(-33.8688, 151.2093)),
    ],
)
def test_parse_valid_decimal_degrees(value, expected):
    assert parse_decimal_degrees(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "not coordinates",
        "42.0",  # only one component
        "42.0, -71.0, 5",  # three components
        "abc, def",
        "91, 0",  # latitude out of range
        "0, 181",  # longitude out of range
        "-90.1, 0",
    ],
)
def test_parse_invalid_returns_none(value):
    assert parse_decimal_degrees(value) is None


def test_location_accessor_matches_parser():
    loc = Location(gps_coordinates="42.3588, -71.0578")
    assert loc.coordinates() == Coordinates(42.3588, -71.0578)


def test_location_without_coords_returns_none():
    assert Location(city="Boston").coordinates() is None


def test_to_dict_emits_structured_coordinates():
    loc = Location(gps_coordinates="42.3588, -71.0578", city="Boston")
    d = loc.to_dict()
    assert d["coordinates"] == {"lat": 42.3588, "lon": -71.0578}
    # Raw spec string is retained alongside the structured form.
    assert d["gps_coordinates"] == "42.3588, -71.0578"


def test_to_dict_omits_coordinates_when_absent_or_invalid():
    assert "coordinates" not in Location(city="Boston").to_dict()
    assert "coordinates" not in Location(gps_coordinates="garbage").to_dict()


def test_spaceapi_uses_the_shared_accessor():
    """MoM/SpaceAPI serialization goes through the same parser (no duplicate)."""
    from src.core.models.okw import FacilityStatus, ManufacturingFacility

    with_coords = ManufacturingFacility(
        name="FabLab",
        location=Location(gps_coordinates="42.3588, -71.0578"),
        facility_status=FacilityStatus.ACTIVE,
    )
    assert with_coords.to_spaceapi_json()["location"] == {
        "lat": 42.3588,
        "lon": -71.0578,
    }

    without = ManufacturingFacility(
        name="NoCoords",
        location=Location(city="Boston"),
        facility_status=FacilityStatus.ACTIVE,
    )
    assert "location" not in without.to_spaceapi_json()
