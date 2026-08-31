"""POST /api/match answers through the in-process client (#432).

It did not. The route is the product's central operation and was the only one
with no in-process contract test — which is why it kept its row in the
response-model allowlist, and why neither of its two payload branches had ever
been asserted anywhere that runs in CI.

The endpoint was never broken. Matching resolves its facility pool through
``resolve_match_facilities``, which under the default ``union`` source queries
Maps of Making over the network; the suite's network guard then raised from
TestClient's worker thread mid-request, and the request produced no response at
all. Pinning the pool to local storage makes the test hermetic, which is what
an integration test should have been anyway.
"""

from __future__ import annotations

import pytest

from tests.record_fixtures import okh_manifest_dict, okw_facility_dict

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def local_facilities_only(monkeypatch):
    """Match against this node's own storage, not the remote catalogue.

    Without this the pool resolver reaches Maps of Making, which an in-process
    test must not do — and the failure it produces looks nothing like a network
    problem.
    """
    monkeypatch.setenv("OKW_SOURCE", "storage")


@pytest.fixture
def shared_design(client):
    """A design matching can see. Created records are private by default."""
    created: list[str] = []

    def make(content: dict) -> str:
        resp = client.post("/api/okh/create", json={"content": content})
        assert resp.status_code == 201, resp.text
        record_id = resp.json()["okh"]["id"]
        created.append(record_id)
        shared = client.put(
            f"/api/okh/{record_id}/visibility", json={"visibility": "public"}
        )
        assert shared.status_code == 200, shared.text
        return record_id

    yield make
    # The client and its storage are session-scoped, so records left behind
    # change what every later test sees.
    for record_id in created:
        client.delete(f"/api/okh/{record_id}")


@pytest.fixture
def a_facility(client):
    created = client.post("/api/okw/create", json={"content": okw_facility_dict()})
    assert created.status_code == 201, created.text
    facility_id = created.json()["okw"]["id"]
    yield facility_id
    client.delete(f"/api/okw/{facility_id}")


def test_match_answers_in_process(client, shared_design, a_facility):
    """The assertion the route has never had: it returns a response at all."""
    okh_id = shared_design(okh_manifest_dict())

    resp = client.post("/api/match", json={"okh_id": okh_id})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    # The payload sits under `data`, and the branch discriminator with it —
    # worth pinning, because #402 recorded it as top-level from a probe against
    # a live server and a model written to that shape would have been wrong.
    assert (
        "matching_mode" in body["data"]
    ), f"no branch discriminator in {sorted(body['data'])}"


def test_the_single_level_branch_is_reachable(client, shared_design, a_facility):
    """A flat manifest takes the flat branch, which carries `solutions`."""
    okh_id = shared_design(okh_manifest_dict())

    data = client.post("/api/match", json={"okh_id": okh_id}).json()["data"]

    # "single-level", hyphenated — not the "single_level" the issue assumed.
    assert data["matching_mode"] == "single-level"
    assert isinstance(data["solutions"], list)
    assert "matching_metrics" in data


def test_a_blocked_network_call_would_now_be_legible(client, shared_design):
    """The guard used to raise a BaseException from a worker thread, which no
    application handler catches — so a blocked call surfaced as a bare 500 that
    read as an application bug. It now raises ConnectionError, which the code
    under test handles like any network failure, and the test fails at teardown
    naming the host.

    Asserted through behaviour rather than by reaching the network: with the
    pool pinned to storage, this request must not touch it at all, and the
    teardown assertion in conftest is what proves it.
    """
    okh_id = shared_design(okh_manifest_dict())

    resp = client.post("/api/match", json={"okh_id": okh_id})

    assert resp.status_code == 200, resp.text
