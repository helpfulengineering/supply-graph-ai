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

from tests.contract_shape import assert_shape
from tests.record_fixtures import okh_manifest_dict, okw_facility_dict

pytestmark = pytest.mark.integration

BLESS = "BLESS_MATCH_CONTRACT"


def test_reverse_match_payload_keeps_every_field_it_declares(client):
    # A design as well as a facility: an empty `designs` list would freeze the
    # envelope and say nothing about the item shape, which is what a client
    # ranks over.
    #
    # The records are created by a REGISTERED caller, and matched as that same
    # caller. New records stamp `private`, and a private record is visible only
    # to the identity that made it — so an anonymous fixture creates a design it
    # then cannot see, and `designs` comes back empty. That is precisely the
    # vacuous golden this test exists to avoid.
    registration = client.post(
        "/api/identity/register", json={"display_name": "Contract Fixture"}
    )
    assert registration.status_code == 201, registration.text
    auth = {"Authorization": f"Bearer {registration.json()['key']['token']}"}

    okh = client.post(
        "/api/okh/create", json={"content": okh_manifest_dict()}, headers=auth
    )
    assert okh.status_code == 201, okh.text
    created = client.post(
        "/api/okw/create", json={"content": okw_facility_dict()}, headers=auth
    )
    assert created.status_code == 201, created.text

    response = client.post(
        "/api/match/facility",
        json={
            "okw_id": created.json()["okw"]["id"],
            "min_confidence": 0.0,
            "max_results": 5,
        },
        headers=auth,
    )
    assert response.status_code == 200, response.text
    assert_shape(response.json(), "match_facility_shape", BLESS)
