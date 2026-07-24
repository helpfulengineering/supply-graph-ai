"""Tests for country code ↔ name normalization."""

from src.core.utils.country_names import (
    countries_match,
    country_match_key,
    display_country_name,
)


def test_display_country_name_codes() -> None:
    assert display_country_name("FR") == "France"
    assert display_country_name("US") == "United States"
    assert display_country_name("France") == "France"


def test_countries_match_code_and_name() -> None:
    assert countries_match("FR", "France")
    assert countries_match("us", "United States")
    assert not countries_match("FR", "DE")
    assert country_match_key("FR") == country_match_key("France")
