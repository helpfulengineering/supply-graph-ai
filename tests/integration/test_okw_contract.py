"""Contract: the OKW template and network-surface payloads, frozen before models.

Lives here rather than in tests/api/ because it needs real data: /spaces is
assembled from stored facilities, and a golden captured against an empty
registry would pin the envelope while saying nothing about the item shape —
which is the half a client actually maps over.

Two different kinds of freeze, deliberately:

* ``/template`` is deterministic, so its golden is the payload itself.
* ``/spaces`` is not. The ``client`` fixture is session-scoped and other
  integration tests create facilities in the same storage, so the list content
  and the counts vary with test order. Freezing those would buy flakiness, not
  safety. Its golden is therefore a SHAPE signature — every key, with values
  replaced by their type — which still fails if a response_model drops a field,
  because a dropped field disappears from the signature.

To change a contract deliberately:
    BLESS_OKW_CONTRACT=1 .venv/bin/python -m pytest \
        tests/integration/test_okw_contract.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.record_fixtures import okw_facility_dict

pytestmark = pytest.mark.integration

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "api" / "golden"


def _shape(node):
    """A value-free description: every key kept, every leaf reduced to a mark.

    Lists collapse to the UNION of their item shapes, so N facilities and one
    facility describe the same contract, and a key present on any record counts
    as present.
    """
    if isinstance(node, dict):
        return {k: _shape(v) for k, v in sorted(node.items())}
    if isinstance(node, list):
        merged: dict = {}
        for item in node:
            shaped = _shape(item)
            if not isinstance(shaped, dict):
                return ["*"]
            for key, value in shaped.items():
                merged.setdefault(key, value)
        return [dict(sorted(merged.items()))] if merged else []
    return "*"


def _check(name: str, body) -> None:
    golden = GOLDEN_DIR / f"{name}.json"
    if os.getenv("BLESS_OKW_CONTRACT"):
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        golden.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
        pytest.skip(f"golden re-blessed: {golden.name}")
    assert golden.exists(), (
        f"No golden at {golden}. Capture one with BLESS_OKW_CONTRACT=1 BEFORE "
        "adding a response_model."
    )
    assert body == json.loads(golden.read_text()), (
        f"{name} changed shape. If a response_model was just added, it is "
        "filtering a field the route used to return."
    )


def test_template_payload_is_field_identical_to_the_golden(client):
    response = client.get("/api/okw/template")
    assert response.status_code == 200, response.text
    _check("okw_template", response.json())


def test_spaces_payload_keeps_every_field_it_declares(client):
    created = client.post("/api/okw/create", json={"content": okw_facility_dict()})
    assert created.status_code == 201, created.text

    # include_mom=false keeps this offline: the MoM union is unit-tested, and a
    # SPARQL call would make the contract depend on someone else's uptime.
    response = client.get("/api/okw/spaces", params={"include_mom": "false"})
    assert response.status_code == 200, response.text
    _check("okw_spaces_shape", _shape(response.json()))
