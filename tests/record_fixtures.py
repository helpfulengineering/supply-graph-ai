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
