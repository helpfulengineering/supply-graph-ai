"""An organisation's admin affiliates members (#578)."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from src.core.models.auth import APIKeyCreate
from src.core.models.identity import IdentityKind
from tests.api.test_affiliation_required import _ada, _auth, _client


async def _grace_token(service, grace) -> str:
    key = await service.create_api_key(
        APIKeyCreate(
            name="grace",
            permissions=["write"],
            account_id=UUID(grace.account_id),
        )
    )
    return key.token


@pytest.mark.asyncio
async def test_the_organisation_admin_can_affiliate_a_member(tmp_path, monkeypatch):
    service = _auth(tmp_path)
    ada, grace, space, _ada_key = await _ada(service)
    token = await _grace_token(service, grace)

    async with _client(monkeypatch, service) as client:
        resp = await client.post(
            "/v1/api/identity/affiliations",
            headers={"Authorization": f"Bearer {token}"},
            json={"space_did": space.did, "subject_did": ada.did},
        )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["issuer_did"] == grace.did
    assert body["subject_did"] == ada.did
    assert "publish" in body["permissions"]
    assert body["scope"]["kind"] == "space"
    assert body["scope"]["target"] == space.did
    expires = datetime.fromisoformat(body["expires_at"])
    remaining = expires - datetime.utcnow()
    assert 89 <= remaining.days <= 90


@pytest.mark.asyncio
async def test_a_member_who_is_not_the_admin_cannot_affiliate(tmp_path, monkeypatch):
    service = _auth(tmp_path)
    _ada_row, _grace, space, ada_key = await _ada(service, permissions=["admin"])
    bob = await service.create_identity(uuid4(), IdentityKind.PERSON, "Bob")

    async with _client(monkeypatch, service) as client:
        resp = await client.post(
            "/v1/api/identity/affiliations",
            headers={"Authorization": f"Bearer {ada_key.token}"},
            json={"space_did": space.did, "subject_did": bob.did},
        )

    assert resp.status_code == 403, resp.text
    assert "admin" in resp.text
    assert await service.list_grants(bob.did) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [180, 7])
async def test_the_affiliation_lasts_as_long_as_the_mode(tmp_path, monkeypatch, days):
    service = _auth(tmp_path)
    ada, grace, space, _ada_key = await _ada(service)
    token = await _grace_token(service, grace)
    monkeypatch.setattr(
        "src.core.services.auth_service.get_security_policy",
        lambda: SimpleNamespace(grant_ttl_days=days),
    )

    async with _client(monkeypatch, service) as client:
        resp = await client.post(
            "/v1/api/identity/affiliations",
            headers={"Authorization": f"Bearer {token}"},
            json={"space_did": space.did, "subject_did": ada.did},
        )

    assert resp.status_code == 201, resp.text
    expires = datetime.fromisoformat(resp.json()["expires_at"])
    remaining = expires - datetime.utcnow()
    assert days - 1 <= remaining.days <= days


@pytest.mark.asyncio
async def test_the_admin_can_unaffiliate_a_member(tmp_path, monkeypatch):
    service = _auth(tmp_path)
    ada, grace, space, ada_key = await _ada(service)
    token = await _grace_token(service, grace)
    async with _client(monkeypatch, service) as client:
        created = await client.post(
            "/v1/api/identity/affiliations",
            headers={"Authorization": f"Bearer {token}"},
            json={"space_did": space.did, "subject_did": ada.did},
        )
        assert created.status_code == 201, created.text
        revoked = await client.delete(
            f"/v1/api/identity/affiliations/{created.json()['grant_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        listed = await client.get(
            "/v1/api/identity/affiliations",
            headers={"Authorization": f"Bearer {ada_key.token}"},
        )

    assert revoked.status_code == 200, revoked.text
    assert listed.status_code == 200, listed.text
    assert listed.json() == []


@pytest.mark.asyncio
async def test_the_admin_can_renew_an_affiliation(tmp_path, monkeypatch):
    service = _auth(tmp_path)
    ada, grace, space, ada_key = await _ada(service)
    token = await _grace_token(service, grace)
    async with _client(monkeypatch, service) as client:
        created = await client.post(
            "/v1/api/identity/affiliations",
            headers={"Authorization": f"Bearer {token}"},
            json={"space_did": space.did, "subject_did": ada.did},
        )
        assert created.status_code == 201, created.text
        renewed = await client.post(
            f"/v1/api/identity/affiliations/{created.json()['grant_id']}/renew",
            headers={"Authorization": f"Bearer {token}"},
        )
        listed = await client.get(
            "/v1/api/identity/affiliations",
            headers={"Authorization": f"Bearer {ada_key.token}"},
        )

    assert renewed.status_code == 201, renewed.text
    body = renewed.json()
    assert body["grant_id"] != created.json()["grant_id"]
    assert body["subject_did"] == ada.did
    assert body["scope"]["target"] == space.did
    expires = datetime.fromisoformat(body["expires_at"])
    remaining = expires - datetime.utcnow()
    assert 89 <= remaining.days <= 90
    assert len(listed.json()) == 1
    assert listed.json()[0]["expires_at"] == body["expires_at"]


@pytest.mark.asyncio
async def test_an_admin_lists_the_people_they_affiliated(tmp_path, monkeypatch):
    service = _auth(tmp_path)
    ada, grace, space, ada_key = await _ada(service)
    token = await _grace_token(service, grace)
    async with _client(monkeypatch, service) as client:
        created = await client.post(
            "/v1/api/identity/affiliations",
            headers={"Authorization": f"Bearer {token}"},
            json={"space_did": space.did, "subject_did": ada.did},
        )
        assert created.status_code == 201, created.text
        grace_list = await client.get(
            "/v1/api/identity/affiliations/administered",
            headers={"Authorization": f"Bearer {token}"},
        )
        ada_list = await client.get(
            "/v1/api/identity/affiliations/administered",
            headers={"Authorization": f"Bearer {ada_key.token}"},
        )

    assert grace_list.status_code == 200, grace_list.text
    rows = grace_list.json()
    assert rows[0]["display_name"] == "FabLab"
    assert rows[0]["space_did"] == space.did
    assert rows[0]["members"][0]["display_name"] == "Ada"
    assert rows[0]["members"][0]["subject_did"] == ada.did
    assert rows[0]["members"][0]["grant_id"] == created.json()["grant_id"]
    assert rows[0]["members"][0]["expires_at"]
    assert ada_list.json() == []
