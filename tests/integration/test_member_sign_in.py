"""A member signs in with a username and password (#570).

The command-line registration, which sends only a display name, still returns
a bearer token. The website registration does not: it sets a session cookie,
and that cookie is what later requests authenticate with.
"""

import time
from uuid import uuid4

import pytest

from src.core.auth.login_limit import clear_login_attempts, note_login_failure

pytestmark = pytest.mark.integration

_PASSWORD = "correct horse"


@pytest.fixture
def member(client):
    client.cookies.clear()
    clear_login_attempts()
    yield client
    client.cookies.clear()
    clear_login_attempts()


def _member(name: str) -> dict:
    return {
        "display_name": name,
        "username": f"{name.lower()}-{uuid4().hex[:8]}",
        "password": _PASSWORD,
    }


def test_registering_with_a_password_sets_a_session_and_no_token(member):
    body = _member("Ada")
    registered = member.post("/api/identity/register", json=body)
    assert registered.status_code == 201, registered.text
    payload = registered.json()
    assert payload["key"] is None
    assert payload["recovery_code"]
    assert "argon2" not in registered.text
    assert member.cookies.get("ohm_session")
    assert member.cookies.get("ohm_csrf")

    me = member.get("/api/identity/whoami")
    assert me.status_code == 200, me.text
    assert me.json()["permissions"] == ["read", "write"]

    stolen = member.cookies.get("ohm_session")
    as_bearer = member.get(
        "/api/identity/whoami",
        headers={"Authorization": f"Bearer {stolen}"},
    )
    assert as_bearer.status_code == 401

    refused = member.post("/api/identity/logout")
    assert refused.status_code == 403

    cross_site = member.post(
        "/api/identity/logout",
        headers={
            "Origin": "https://evil.example",
            "X-OHM-CSRF": member.cookies.get("ohm_csrf"),
        },
    )
    assert cross_site.status_code == 403
    assert member.get("/api/identity/whoami").status_code == 200

    csrf = member.cookies.get("ohm_csrf")
    signed_out = member.post("/api/identity/logout", headers={"X-OHM-CSRF": csrf})
    assert signed_out.status_code == 204
    assert member.get("/api/identity/whoami").status_code == 401


def test_login_accepts_the_password_and_rejects_a_wrong_one_the_same_way(member):
    body = _member("Grace")
    assert member.post("/api/identity/register", json=body).status_code == 201
    member.cookies.clear()

    wrong = member.post(
        "/api/identity/login",
        json={"username": body["username"], "password": "not-the-password"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["detail"] == "Username or password is incorrect."

    missing = member.post(
        "/api/identity/login",
        json={"username": "nobody-here", "password": _PASSWORD},
    )
    assert missing.status_code == 401
    assert missing.json()["detail"] == "Username or password is incorrect."

    signed_in = member.post(
        "/api/identity/login",
        json={"username": body["username"].upper(), "password": _PASSWORD},
    )
    assert signed_in.status_code == 200, signed_in.text
    assert member.get("/api/identity/whoami").status_code == 200


def test_a_username_can_be_taken_only_once(member):
    body = _member("Katherine")
    assert member.post("/api/identity/register", json=body).status_code == 201
    again = member.post("/api/identity/register", json=body)
    assert again.status_code == 409
    assert again.json()["detail"] == "That username is already taken."


def test_login_slows_down_after_repeated_failures(member):
    body = _member("Slow")
    assert member.post("/api/identity/register", json=body).status_code == 201
    moment = time.monotonic()
    for _ in range(5):
        note_login_failure(body["username"], now=moment)

    slowed = member.post(
        "/api/identity/login",
        json={"username": body["username"], "password": _PASSWORD},
    )
    assert slowed.status_code == 429


def test_a_display_name_alone_still_returns_a_token(member):
    registered = member.post(
        "/api/identity/register", json={"display_name": "Command Line"}
    )
    assert registered.status_code == 201, registered.text
    assert registered.json()["key"]["token"]


def test_the_public_policy_names_the_node_and_its_operator(client, monkeypatch):
    from src.config import settings

    monkeypatch.setattr(settings, "OHM_FEDERATION_NODE_NAME", "Harbor Node")
    monkeypatch.setattr(settings, "OHM_NODE_OPERATOR", "Ada Lovelace")
    resp = client.get("/api/identity/security-policy")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["node_name"] == "Harbor Node"
    assert body["operator_name"] == "Ada Lovelace"


def test_a_cross_site_login_is_refused(member):
    refused = member.post(
        "/api/identity/login",
        json={"username": "ada", "password": _PASSWORD},
        headers={"Origin": "https://evil.example"},
    )
    assert refused.status_code == 403


def test_recovery_sets_a_new_password_and_signs_this_browser_in(member):
    body = _member("Ada")
    registered = member.post("/api/identity/register", json=body)
    assert registered.status_code == 201, registered.text
    code = registered.json()["recovery_code"]
    old_session = member.cookies.get("ohm_session")
    member.cookies.clear()

    recovered = member.post(
        "/api/identity/recover",
        json={"code": code, "password": "brand new horse"},
    )
    assert recovered.status_code == 200, recovered.text
    payload = recovered.json()
    assert payload["key"] is None
    assert payload["recovery_code"]
    assert payload["recovery_code"] != code
    assert member.cookies.get("ohm_session")
    assert member.cookies.get("ohm_session") != old_session
    assert member.get("/api/identity/whoami").status_code == 200

    member.cookies.clear()
    member.cookies.set("ohm_session", old_session)
    assert member.get("/api/identity/whoami").status_code == 401

    member.cookies.clear()
    signed_in = member.post(
        "/api/identity/login",
        json={"username": body["username"], "password": "brand new horse"},
    )
    assert signed_in.status_code == 200, signed_in.text
    member.cookies.clear()
    wrong = member.post(
        "/api/identity/login",
        json={"username": body["username"], "password": _PASSWORD},
    )
    assert wrong.status_code == 401

    refused = member.post(
        "/api/identity/recover",
        json={"code": payload["recovery_code"], "password": "short"},
    )
    assert refused.status_code == 422
    again = member.post(
        "/api/identity/recover",
        json={"code": payload["recovery_code"], "password": "another good horse"},
    )
    assert again.status_code == 200, again.text


def test_recovering_without_a_password_still_returns_a_token(member):
    registered = member.post(
        "/api/identity/register", json={"display_name": "Command Line"}
    )
    assert registered.status_code == 201, registered.text
    token = registered.json()["key"]["token"]
    recovered = member.post(
        "/api/identity/recover",
        json={"code": registered.json()["recovery_code"]},
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["key"]["token"]
    assert recovered.json()["key"]["token"] != token
    stale = member.get(
        "/api/identity/whoami",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert stale.status_code == 401
