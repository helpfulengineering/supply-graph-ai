"""Service <-> API <-> CLI parity gate.

Enumerates the real codebase and asserts it matches the declared contract in
``manifest.py``. This is the ratchet that stops new layer-drift: you cannot add
a service, route, or CLI group without recording how it is exposed.

When this fails, do ONE of:
  * wire the missing layer(s) for the new feature, or
  * add a row to ``tests/parity/manifest.py`` classifying it (e.g. internal).

Run directly with:  uv run pytest tests/parity -q
"""

from __future__ import annotations

import os

import pytest

from tests.parity.inventory import (
    actual_api_tags,
    actual_cli_groups,
    actual_fe_api_prefixes,
    actual_fe_routes,
    actual_services,
)
from tests.parity.manifest import (
    expected_api_tags,
    expected_cli_groups,
    expected_fe_api_prefixes,
    expected_fe_routes,
    expected_services,
)

pytestmark = pytest.mark.contract

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def _diff_message(layer: str, expected: set[str], actual: set[str]) -> str:
    undeclared = sorted(actual - expected)  # in code, not in manifest
    missing = sorted(expected - actual)  # in manifest, not in code
    lines = [f"{layer} parity drift detected:"]
    if undeclared:
        lines.append(
            f"  UNDECLARED (present in code, absent from manifest): {undeclared}\n"
            f"    -> add a row to tests/parity/manifest.py classifying each."
        )
    if missing:
        lines.append(
            f"  MISSING (declared in manifest, absent from code): {missing}\n"
            f"    -> a rename/deletion broke the contract; fix the code or the row."
        )
    return "\n".join(lines)


# --- the gate ------------------------------------------------------------


def test_services_match_manifest():
    expected, actual = expected_services(), actual_services()
    assert expected == actual, _diff_message("Service", expected, actual)


def test_api_tags_match_manifest():
    expected, actual = expected_api_tags(), actual_api_tags()
    assert expected == actual, _diff_message("API tag", expected, actual)


def test_cli_groups_match_manifest():
    expected, actual = expected_cli_groups(), actual_cli_groups()
    assert expected == actual, _diff_message("CLI group", expected, actual)


def test_fe_routes_match_manifest():
    expected, actual = expected_fe_routes(), actual_fe_routes()
    assert expected == actual, _diff_message("Frontend route", expected, actual)


def test_fe_api_prefixes_match_manifest():
    expected, actual = expected_fe_api_prefixes(), actual_fe_api_prefixes()
    assert expected == actual, _diff_message("Frontend API prefix", expected, actual)


def test_manifest_has_no_duplicate_slots():
    """No two areas may claim the same service / tag / CLI group."""
    from tests.parity.manifest import AREAS

    for slot in ("service", "api_tag", "cli_group", "fe_routes", "fe_api_prefixes"):
        values: list[str] = []
        for area in AREAS:
            raw = getattr(area, slot)
            if raw is None:
                continue
            if isinstance(raw, tuple):
                values.extend(raw)
            else:
                values.append(raw)
        dupes = sorted({v for v in values if values.count(v) > 1})
        assert not dupes, f"Duplicate {slot} declared in manifest: {dupes}"
