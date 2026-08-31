"""Break-glass costs the admin their anonymity, not the user their privacy (#406).

An admin's standing scope is unchanged: they do not read private records. This
is the exception, available only in crisis, and its price is a durable record
that the person whose record was read can see.

The test that matters most is the last one: an accounting the subject cannot
read is not an accounting, and before this the whole attestation surface was
admin-only — so the one person it was written for was the one person who could
not see it.
"""

from __future__ import annotations

import pytest

from src.config.security_policy import SecurityMode, get_security_policy
from tests.record_fixtures import okh_manifest_dict

pytestmark = pytest.mark.integration

REASON = "Recovering a contributor's work after they lost their key"


def _register(client, name="Break Glass Fixture"):
    resp = client.post("/api/identity/register", json={"display_name": name})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return {"Authorization": f"Bearer {body['key']['token']}"}, body["did"]


@pytest.fixture
def node_identity(tmp_path, monkeypatch):
    """Give the node a signing identity, the way a real node has one.

    Break-glass refuses outright when the node cannot sign the access record —
    no accounting, no access — so exercising the happy path means the node has
    to actually hold a key. Written through `load_or_create_identity` rather
    than by patching internals, so the test uses the same path production does.
    """
    from src.core.federation.identity import load_or_create_identity
    from src.core.services.auth_service import AuthenticationService

    data_dir = tmp_path / "federation"
    identity = load_or_create_identity(data_dir, "test-node")
    monkeypatch.setattr("src.config.settings.OHM_FEDERATION_DATA_DIR", str(data_dir))
    # The service caches the identity after first read; drop it so the patched
    # path is what gets loaded.
    if AuthenticationService._instance is not None:
        AuthenticationService._instance._node_signing = None
    yield identity
    if AuthenticationService._instance is not None:
        AuthenticationService._instance._node_signing = None


def _crisis(monkeypatch):
    crisis = get_security_policy(SecurityMode.CRISIS)
    for module in (
        "src.core.api.routes.okh",
        "src.core.api.routes.okw",
    ):
        monkeypatch.setattr(f"{module}.get_security_policy", lambda: crisis)


@pytest.fixture
def a_private_design(client):
    """Create designs, and take them away again.

    The integration client is session-scoped and so is its storage, so records
    left behind change what every later test sees — a catalogue that grew under
    them made three unrelated specs fail. Tests that add to the shared world
    have to remove what they added.
    """
    created: list[str] = []

    def make(auth) -> str:
        resp = client.post(
            "/api/okh/create", json={"content": okh_manifest_dict()}, headers=auth
        )
        assert resp.status_code == 201, resp.text
        record_id = resp.json()["okh"]["id"]
        created.append(record_id)
        return record_id

    yield make

    for record_id in created:
        client.delete(f"/api/okh/{record_id}")


def test_peacetime_refuses_and_names_the_mode(client, a_private_design):
    auth, _ = _register(client)
    record_id = a_private_design(auth)

    resp = client.post(
        f"/api/okh/{record_id}/break-glass", json={"reason": REASON}, headers=auth
    )

    assert resp.status_code == 403, resp.text
    assert "peacetime" in resp.text


def test_crisis_returns_the_record(
    client, monkeypatch, node_identity, a_private_design
):
    auth, _ = _register(client)
    record_id = a_private_design(auth)
    _crisis(monkeypatch)

    resp = client.post(
        f"/api/okh/{record_id}/break-glass", json={"reason": REASON}, headers=auth
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == record_id


@pytest.mark.parametrize("reason", ["", "   ", "too short"])
def test_a_missing_or_thin_reason_is_rejected(
    client, monkeypatch, reason, a_private_design
):
    """The reason is the point. Without one this is a standing permission with
    extra steps."""
    auth, _ = _register(client)
    record_id = a_private_design(auth)
    _crisis(monkeypatch)

    resp = client.post(
        f"/api/okh/{record_id}/break-glass", json={"reason": reason}, headers=auth
    )
    assert resp.status_code == 422, resp.text

    missing = client.post(f"/api/okh/{record_id}/break-glass", json={}, headers=auth)
    assert missing.status_code == 422


def test_the_owner_can_see_that_their_record_was_read(
    client, monkeypatch, node_identity, a_private_design
):
    """The whole design in one assertion.

    The attestation names the admin, the record and the reason, and its subject
    is the owner — so it turns up in the owner's own attestation list, which is
    scoped to them rather than admin-only.
    """
    auth, owner_did = _register(client, "Ada")
    record_id = a_private_design(auth)
    _crisis(monkeypatch)

    read = client.post(
        f"/api/okh/{record_id}/break-glass", json={"reason": REASON}, headers=auth
    )
    assert read.status_code == 200, read.text

    mine = client.get("/api/identity/attestations", headers=auth).json()
    accesses = [a for a in mine if a["type"] == "admin_access"]

    assert accesses, f"the owner cannot see the access: {mine}"
    claim = accesses[0]["claim"]
    assert accesses[0]["subject_did"] == owner_did
    assert claim["record_id"] == record_id
    assert claim["reason"] == REASON
    assert claim["accessed_by_did"]


def test_break_glass_grants_nothing_standing(
    client, monkeypatch, node_identity, a_private_design
):
    """Reading one record must not widen what the admin can list."""
    auth, _ = _register(client)
    record_id = a_private_design(auth)
    other_auth, _ = _register(client, "Someone Else")
    other_id = a_private_design(other_auth)
    _crisis(monkeypatch)

    client.post(
        f"/api/okh/{record_id}/break-glass", json={"reason": REASON}, headers=auth
    )

    # The caller still sees only their own records, not the other account's.
    listed = client.get("/api/okh?page_size=100", headers=auth).json()["items"]
    assert other_id not in [r["id"] for r in listed]


def test_a_node_that_cannot_record_the_access_refuses_it(
    client, monkeypatch, a_private_design
):
    """No accounting, no access.

    Break-glass without a record is just an admin reading a private record,
    which is the thing the boundary forbids. Checked before the read, so a node
    that cannot sign never makes the access in the first place.
    """
    auth, _ = _register(client)
    record_id = a_private_design(auth)
    _crisis(monkeypatch)
    monkeypatch.setattr(
        "src.config.settings.OHM_FEDERATION_DATA_DIR", "/nonexistent-for-this-test"
    )
    from src.core.services.auth_service import AuthenticationService

    if AuthenticationService._instance is not None:
        AuthenticationService._instance._node_signing = None

    resp = client.post(
        f"/api/okh/{record_id}/break-glass", json={"reason": REASON}, headers=auth
    )

    assert resp.status_code == 503, resp.text
    assert "record of the access" in resp.text
