"""Both branches of POST /api/match, captured before modelling them (#373).

The last row on the ALLOWLIST, and the one that waited longest. The endpoint
returns two structurally different payloads chosen by ``matching_mode``:
single-level answers with ``solutions`` (a list) and ``matching_metrics``,
nested with ``solution`` (one) and ``validation_result``. One flat model would
filter whichever branch it is not, so the response model is a union
discriminated on ``matching_mode`` — and a union can only be trusted if both
arms are frozen.

It could not be captured until now. The single-level branch 500'd until #434
(#432), and the nested branch until #441 (#439).

Each branch is captured twice, saved and unsaved, because several fields are
conditional: ``solution_id`` appears only when ``save_solution`` was asked for,
and ``human_summary`` and ``save_warning`` likewise. A model that declared them
required would reject the plain call; one that omitted them would drop the
saved solution's id, which is the only way a caller learns where its result
went.

    BLESS_MATCH=1 .venv/bin/python -m pytest \
        tests/integration/test_match_contract.py
"""

from __future__ import annotations

import pytest

from tests.contract_shape import assert_shape
from tests.record_fixtures import okh_nested_assembly_dict, okw_facility_dict

pytestmark = pytest.mark.integration

BLESS = "BLESS_MATCH"


@pytest.fixture
def matchable(client, monkeypatch):
    """A design with a two-level BOM, and a facility that can make it."""
    # Storage-only facilities: the default unions in the Map of Manufacturers,
    # which is a network call the suite's guard blocks.
    monkeypatch.setenv("OKW_SOURCE", "storage")

    registration = client.post(
        "/api/identity/register", json={"display_name": "Match Contract Fixture"}
    )
    assert registration.status_code == 201, registration.text
    auth = {"Authorization": f"Bearer {registration.json()['key']['token']}"}

    okh = client.post(
        "/api/okh/create",
        json={"content": okh_nested_assembly_dict()},
        headers=auth,
    )
    assert okh.status_code == 201, okh.text
    okw = client.post(
        "/api/okw/create", json={"content": okw_facility_dict()}, headers=auth
    )
    assert okw.status_code == 201, okw.text
    return auth, okh.json()["okh"]["id"]


def _mask_projections(body):
    """Blank the interiors of ``facility`` and ``tree`` inside each solution.

    Those are OKW and SupplyTree projections of *whatever records exist*, and
    the integration client is session-scoped: which facility ranks first
    depends on what other tests left in shared storage, so their interiors
    differ between runs of the same suite. Freezing them makes a strict-looking
    golden that is really a flaky one — this failed only in a full run, and
    only sometimes.

    Nothing is lost by masking them. The response model types ``solutions`` as
    ``List[Dict[str, Any]]`` precisely because these projections carry optional
    keys, so it cannot filter anything *inside* a solution item. What the
    golden has to protect is the set of keys the model does declare: the
    top-level ``data`` keys, and the keys of each solution item. Both are still
    frozen.
    """
    data = body.get("data") or {}
    for solution in data.get("solutions") or []:
        for key in ("facility", "tree"):
            if key in solution:
                solution[key] = "<projection>"
    return body


def _match(client, auth, okh_id, **overrides):
    body = {"okh_id": okh_id, "min_confidence": 0.0}
    body.update(overrides)
    response = client.post("/api/match", json=body, headers=auth)
    assert response.status_code == 200, response.text
    return response


def test_single_level_shape(client, matchable):
    auth, okh_id = matchable
    response = _match(client, auth, okh_id, max_depth=0, include_explanation=True)
    data = response.json()["data"]
    assert data["matching_mode"] == "single-level"
    assert data["solutions"], "an empty solutions list freezes no item shape"
    # Only present when asked for, and the UI reads both.
    assert "explanation" in data["solutions"][0]
    assert_shape(_mask_projections(response.json()), "match_single_level", BLESS)


def test_single_level_saved_shape(client, matchable):
    """`solution_id` appears only here. A model without it drops it silently."""
    auth, okh_id = matchable
    response = _match(
        client, auth, okh_id, max_depth=0, include_explanation=True, save_solution=True
    )
    assert response.json()["data"]["solution_id"]
    assert_shape(_mask_projections(response.json()), "match_single_level_saved", BLESS)


def test_nested_shape(client, matchable):
    auth, okh_id = matchable
    response = _match(client, auth, okh_id, max_depth=2)
    data = response.json()["data"]
    assert data["matching_mode"] == "nested"
    # The other arm of the union: one solution, not a list of them.
    assert "solution" in data and "solutions" not in data
    assert data["solution"]["all_trees"], "nested match produced no trees"
    assert_shape(response.json(), "match_nested", BLESS)


def test_nested_saved_shape(client, matchable):
    auth, okh_id = matchable
    response = _match(client, auth, okh_id, max_depth=2, save_solution=True)
    assert response.json()["data"]["solution_id"]
    assert_shape(response.json(), "match_nested_saved", BLESS)
