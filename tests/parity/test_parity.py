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

import glob
import os

import pytest

from tests.parity.manifest import (
    TOP_LEVEL_CLI,
    expected_api_tags,
    expected_cli_groups,
    expected_services,
)

pytestmark = pytest.mark.contract

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


# --- live enumeration of the real codebase -------------------------------


def actual_services() -> set[str]:
    """Service stems from ``src/core/services/*_service.py``."""
    pattern = os.path.join(_REPO_ROOT, "src", "core", "services", "*_service.py")
    return {
        os.path.basename(path)[: -len("_service.py")] for path in glob.glob(pattern)
    }


def actual_api_tags() -> set[str]:
    """Router tags actually mounted on the versioned FastAPI app."""
    from src.core.main import api_v1

    tags: set[str] = set()
    for route in api_v1.routes:
        for tag in getattr(route, "tags", None) or []:
            tags.add(tag)
    return tags


def actual_cli_groups() -> set[str]:
    """Click groups actually registered on the CLI, minus top-level utilities."""
    from src.cli.main import cli

    return set(cli.commands.keys()) - TOP_LEVEL_CLI


# --- helpers -------------------------------------------------------------


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


def test_manifest_has_no_duplicate_slots():
    """No two areas may claim the same service / tag / CLI group."""
    from tests.parity.manifest import AREAS

    for slot in ("service", "api_tag", "cli_group"):
        values = [getattr(a, slot) for a in AREAS if getattr(a, slot) is not None]
        dupes = sorted({v for v in values if values.count(v) > 1})
        assert not dupes, f"Duplicate {slot} declared in manifest: {dupes}"
