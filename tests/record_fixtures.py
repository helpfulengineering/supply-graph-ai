"""Minimal OKH/OKW records for tests (committed under tests/matching/fixtures).

The historical ``synthetic_data/`` tree is no longer shipped with the repo.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_FIXTURES = Path(__file__).resolve().parent / "matching" / "fixtures"


def okw_facility_dict() -> Dict[str, Any]:
    return json.loads(
        (_FIXTURES / "okw_additive_local.json").read_text(encoding="utf-8")
    )


def okh_manifest_dict() -> Dict[str, Any]:
    return json.loads((_FIXTURES / "okh_3dp_only.json").read_text(encoding="utf-8"))


def okh_nested_assembly_dict() -> Dict[str, Any]:
    """A manifest with a genuinely two-level ``sub_parts`` tree.

    ``_has_nested_components`` keys on the manifest's own ``sub_parts``, and it
    is what sends POST /api/match down its nested branch. Without a fixture
    that reaches it, half the endpoint's response shapes were never exercised.

    The nesting has to live *here*, at the top level. It used to sit inside
    ``parts[0].sub_parts``, where nothing reads it: ``PartSpec`` has no
    ``sub_parts`` field, so it was dropped at parse time. The fixture parsed,
    looked nested, and exercised a single-component BOM — and auto-detection
    never fired for it at all.
    """
    return json.loads(
        (_FIXTURES / "okh_nested_assembly.json").read_text(encoding="utf-8")
    )
