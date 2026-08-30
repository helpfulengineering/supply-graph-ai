"""Contract: POST /api/match/facility is shape-frozen before it gains a model.

Reverse matching: given an OKW facility, which OKH designs can it produce.

Frozen structurally rather than by value. The integration ``client`` fixture is
session-scoped, so the designs this returns depend on which OKH records other
tests created — value-freezing that would be a flaky test dressed as a strict
one (see tests/api/test_filetypes_utility_contract.py, where exactly that had
to be undone). Keys are what a ``response_model`` can drop, so keys are what
this freezes.

To change the contract deliberately:
    BLESS_MATCH_CONTRACT=1 .venv/bin/python -m pytest \
        tests/integration/test_match_facility_contract.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.record_fixtures import okh_manifest_dict, okw_facility_dict

pytestmark = pytest.mark.integration

GOLDEN = (
    Path(__file__).resolve().parents[1] / "api" / "golden" / "match_facility_shape.json"
)


def _structure(node):
    """Every key kept, every leaf reduced to a mark; lists merged to one item."""
    if isinstance(node, dict):
        return {k: _structure(v) for k, v in sorted(node.items())}
    if isinstance(node, list):
        merged: dict = {}
        for item in node:
            shaped = _structure(item)
            if not isinstance(shaped, dict):
                return ["*"]
            for key, value in shaped.items():
                merged.setdefault(key, value)
        return [dict(sorted(merged.items()))] if merged else []
    return "*"


def test_reverse_match_payload_keeps_every_field_it_declares(client):
    # A design as well as a facility: an empty `designs` list would freeze the
    # envelope and say nothing about the item shape, which is what a client
    # ranks over.
    okh = client.post("/api/okh/create", json={"content": okh_manifest_dict()})
    assert okh.status_code == 201, okh.text
    created = client.post("/api/okw/create", json={"content": okw_facility_dict()})
    assert created.status_code == 201, created.text

    response = client.post(
        "/api/match/facility",
        json={
            "okw_id": created.json()["okw"]["id"],
            "min_confidence": 0.0,
            "max_results": 5,
        },
    )
    assert response.status_code == 200, response.text
    body = _structure(response.json())

    if os.getenv("BLESS_MATCH_CONTRACT"):
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
        pytest.skip("golden re-blessed")

    assert GOLDEN.exists(), (
        f"No golden at {GOLDEN}. Capture one with BLESS_MATCH_CONTRACT=1 BEFORE "
        "adding a response_model."
    )
    assert body == json.loads(GOLDEN.read_text()), (
        "POST /api/match/facility changed shape. If a response_model was just "
        "added, it is filtering a field the route used to return."
    )
