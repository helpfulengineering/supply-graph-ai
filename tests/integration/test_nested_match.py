"""Nested matching, end to end (#439).

``POST /api/match`` with ``max_depth > 0`` returned a bare 500 for every
caller. The handler is annotated ``-> dict[str, Any]``, which FastAPI uses as
the response model when none is declared; ``@api_endpoint`` passes a Pydantic
model straight through rather than wrapping it, so the nested branch returning
``create_success_response(...)`` failed response validation. The whole payload
was computed and then thrown away.

Nothing exercised the nested branch, which is why that survived. These tests
are the coverage that was missing, and they assert more than a 200: that the
response really is nested, that a deeper ``max_depth`` reaches deeper into the
BOM, and that the envelope matches the single-level branch — the specific
things a "just make it return a dict" fix could get wrong.
"""

from __future__ import annotations

import pytest

from tests.record_fixtures import okh_nested_assembly_dict, okw_facility_dict

pytestmark = pytest.mark.integration

ENVELOPE_KEYS = {"status", "message", "timestamp", "request_id", "data", "metadata"}


@pytest.fixture
def nested_design(client, monkeypatch):
    """A registered caller, a two-level design and a facility that can make it."""
    # Storage-only facilities: the default unions in the Map of Manufacturers,
    # which is a network call the suite's guard blocks.
    monkeypatch.setenv("OKW_SOURCE", "storage")

    registration = client.post(
        "/api/identity/register", json={"display_name": "Nested Match Fixture"}
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


def _match(client, auth, okh_id, **overrides):
    body = {"okh_id": okh_id, "min_confidence": 0.0}
    body.update(overrides)
    return client.post("/api/match", json=body, headers=auth)


def test_nested_match_succeeds(client, nested_design):
    """The regression: max_depth > 0 used to 500 unconditionally."""
    auth, okh_id = nested_design
    response = _match(client, auth, okh_id, max_depth=2)

    assert response.status_code == 200, response.text
    body = response.json()
    assert ENVELOPE_KEYS <= set(body), (
        "nested responses must carry the same envelope as single-level ones; "
        "returning the envelope object itself is what caused #439"
    )
    assert body["status"] == "success"
    assert body["data"]["matching_mode"] == "nested"


def test_nested_match_returns_a_real_nested_solution(client, nested_design):
    """A 200 carrying an empty solution would satisfy the fix and nothing else."""
    auth, okh_id = nested_design
    body = _match(client, auth, okh_id, max_depth=2).json()

    solution = body["data"]["solution"]
    assert solution["is_nested"] is True
    assert solution["all_trees"], "nested match produced no supply trees"

    metadata = solution["metadata"]
    assert metadata["matched_components"] >= 1
    assert metadata["unmatched_components"] == 0
    # The empty-BOM fallback returns a solution carrying this instead of trees.
    assert "warning" not in metadata, metadata.get("warning")


def test_deeper_max_depth_reaches_deeper_into_the_bom(client, nested_design):
    """max_depth has to actually explode the BOM, not just select the branch.

    The design is two levels — a Housing holding a Clip. At depth 1 only the
    Housing is a component; at depth 2 the Clip is reached as well. Without
    this, a fix that routed to nested matching and then explored nothing would
    still pass every other test here.
    """
    auth, okh_id = nested_design

    def components_at(depth: int) -> int:
        body = _match(client, auth, okh_id, max_depth=depth).json()
        return body["data"]["solution"]["metadata"]["component_count"]

    shallow, deep = components_at(1), components_at(2)
    assert deep > shallow, (
        f"depth 2 found {deep} components and depth 1 found {shallow}; "
        "the BOM is not being explored"
    )

    depths = {
        tree.get("depth")
        for tree in _match(client, auth, okh_id, max_depth=2).json()["data"][
            "solution"
        ]["all_trees"]
    }
    assert depths >= {0, 1}, f"expected trees at two levels, saw depths {depths}"


def test_auto_detect_depth_selects_nested_matching(client, nested_design):
    """The other way into the nested branch, and the other way to hit #439.

    A caller who never sends max_depth still lands here when the manifest has
    nested sub_parts, so this path was equally broken and equally uncovered.
    """
    auth, okh_id = nested_design
    response = _match(client, auth, okh_id, auto_detect_depth=True)

    assert response.status_code == 200, response.text
    assert response.json()["data"]["matching_mode"] == "nested"


def test_single_level_is_unchanged(client, nested_design):
    """The branch that already worked still does, and still differs in shape."""
    auth, okh_id = nested_design
    body = _match(client, auth, okh_id, max_depth=0).json()

    assert body["data"]["matching_mode"] == "single-level"
    # Single-level returns a list of solutions; nested returns one. Collapsing
    # that difference is the other way to "fix" this endpoint wrongly.
    assert "solutions" in body["data"]
    assert "solution" not in body["data"]
