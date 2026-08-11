"""Normalize ISO country codes to English display names for UI / filter matching."""

from __future__ import annotations

from typing import Optional

# Keep in sync with frontend/src/features/match/geoDisplay.ts COUNTRY_NAMES.
COUNTRY_NAMES: dict[str, str] = {
    "AD": "Andorra",
    "AE": "United Arab Emirates",
    "AR": "Argentina",
    "AT": "Austria",
    "AU": "Australia",
    "BE": "Belgium",
    "BR": "Brazil",
    "CA": "Canada",
    "CH": "Switzerland",
    "CL": "Chile",
    "CN": "China",
    "CO": "Colombia",
    "CZ": "Czechia",
    "DE": "Germany",
    "DK": "Denmark",
    "ES": "Spain",
    "FI": "Finland",
    "FR": "France",
    "GB": "United Kingdom",
    "GR": "Greece",
    "HK": "Hong Kong",
    "HU": "Hungary",
    "IE": "Ireland",
    "IL": "Israel",
    "IN": "India",
    "IT": "Italy",
    "JP": "Japan",
    "KR": "South Korea",
    "MX": "Mexico",
    "NL": "Netherlands",
    "NO": "Norway",
    "NZ": "New Zealand",
    "PL": "Poland",
    "PT": "Portugal",
    "RO": "Romania",
    "RU": "Russia",
    "SE": "Sweden",
    "SG": "Singapore",
    "TH": "Thailand",
    "TR": "Turkey",
    "TW": "Taiwan",
    "UA": "Ukraine",
    "US": "United States",
    "USA": "United States",
    "ZA": "South Africa",
}

_BY_NAME = {name.lower(): code for code, name in COUNTRY_NAMES.items()}


def display_country_name(raw: Optional[str]) -> str:
    """Return English country name; pass through unknown values unchanged."""
    if not raw or not str(raw).strip():
        return ""
    s = str(raw).strip()
    upper = s.upper()
    return COUNTRY_NAMES.get(upper, s)


def country_match_key(raw: Optional[str]) -> str:
    """Canonical lowercase key so FR and France compare equal."""
    if not raw or not str(raw).strip():
        return ""
    s = str(raw).strip()
    upper = s.upper()
    if upper in COUNTRY_NAMES:
        return COUNTRY_NAMES[upper].lower()
    code = _BY_NAME.get(s.lower())
    if code:
        return COUNTRY_NAMES[code].lower()
    return s.lower()


def countries_match(a: Optional[str], b: Optional[str]) -> bool:
    ka, kb = country_match_key(a), country_match_key(b)
    return bool(ka) and ka == kb


# Names back to ISO 3166-1 alpha-2 only. COUNTRY_NAMES also carries the
# non-standard "USA" alias, so the general reverse map above can answer with a
# three-letter code; a consumer expecting alpha-2 would take that as valid.
_BY_NAME_ALPHA2 = {
    name.lower(): code for code, name in COUNTRY_NAMES.items() if len(code) == 2
}


def country_code(raw: Optional[str]) -> str:
    """Return the ISO 3166-1 alpha-2 code for a code or English name, else "".

    Empty for anything not in the table, so callers can omit the field rather
    than publish a guess — this feeds interop formats where a wrong code is
    worse than an absent one.
    """
    if not raw or not str(raw).strip():
        return ""
    s = str(raw).strip()
    upper = s.upper()
    if upper not in COUNTRY_NAMES:
        return _BY_NAME_ALPHA2.get(s.lower(), "")
    if len(upper) == 2:
        return upper
    # A known but non-alpha-2 key such as "USA": resolve via its display name.
    return _BY_NAME_ALPHA2.get(COUNTRY_NAMES[upper].lower(), "")
