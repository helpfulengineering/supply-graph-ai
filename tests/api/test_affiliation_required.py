"""Publishing for an organisation requires an affiliation (#577)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI

from src.core.federation.identity import generate_identity
from src.core.models.auth import APIKeyCreate
from src.core.models.capability import Scope
from src.core.models.identity import IdentityKind
from src.core.services.auth_service import AuthenticationService
from src.core.storage.auth_storage import AuthStorage
from src.core.storage.grant_store import GrantStore
from src.core.storage.identity_key_store import IdentityKeyStore
from src.core.storage.space_claim_store import SpaceClaimStore

MINIMAL = {
    "okhv": "1.0",
    "id": str(uuid4()),
    "title": "Affiliation seed",
    "version": "1.0.0",
    "license": {"hardware": "MIT"},
    "licensor": "OHM Test",
    "documentation_language": "en",
    "function": "A design published for an organisation",
    "manufacturing_processes": ["Assembly"],
}

FACILITY = {
    "name": "Open Shop",
    "location": {"address": {"city": "Somewhere", "country": "GB"}},
    "facility_status": "Active",
}


class _InMemoryManager:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def put_object(self, key, data, content_type=None, metadata=None):
        self._objects[key] = data

    async def get_object(self, key):
        return self._objects[key]

    async def delete_object(self, key):
        self._objects.pop(key, None)

    async def list_objects(self, prefix=None):
        for key, data in list(self._objects.items()):
            if prefix is None or key.startswith(prefix):
                yield {"key": key, "data": data}


class _FakeStorageService:
    def __init__(self) -> None:
        self.manager = _InMemoryManager()


def _auth(tmp_path) -> AuthenticationService:
    backing = _FakeStorageService()
    svc = AuthenticationService()
    svc._auth_storage = AuthStorage(backing)
    svc._grant_store = GrantStore(backing)
    svc._space_claim_store = SpaceClaimStore(backing)
    svc._identity_store = IdentityKeyStore(tmp_path)
    svc._node_signing = generate_identity("test-node")
    svc._initialized = True
    return svc


def _use(monkeypatch, service):
    async def get_instance(cls):
        return service

    monkeypatch.setattr(
        AuthenticationService, "get_instance", classmethod(get_instance)
    )


def _okh():
    from src.core.models.okh import OKHManifest

    okh = MagicMock()
    okh.create = AsyncMock(return_value=OKHManifest.from_dict(dict(MINIMAL)))
    return okh


async def _ada(service, permissions=None):
    """A person, a claimed organisation, and that person's API key. No grant."""
    account = uuid4()
    ada = await service.create_identity(account, IdentityKind.PERSON, "Ada")
    space = await service.create_identity(uuid4(), IdentityKind.SPACE, "FabLab")
    admin = await service.create_identity(uuid4(), IdentityKind.PERSON, "Grace")
    await service.claim_space(space.did, admin.did)
    key = await service.create_api_key(
        APIKeyCreate(
            name="ada",
            permissions=permissions or ["write"],
            account_id=account,
        )
    )
    return ada, admin, space, key


@asynccontextmanager
async def _client(monkeypatch, service=None, overrides=None):
    if service is not None:
        _use(monkeypatch, service)
    from src.core.main import api_v1

    for dependency, override in (overrides or {}).items():
        api_v1.dependency_overrides[dependency] = override
    app = FastAPI()
    app.mount("/v1", api_v1)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            yield client
    finally:
        api_v1.dependency_overrides.clear()


async def _publish(client, organisation, token=None, path="/v1/api/okh/create"):
    headers = {"Authorization": f"Bearer {token}"} if token else None
    body = {"content": MINIMAL} if path.endswith("/create") else MINIMAL
    return await client.post(
        path,
        params={"on_behalf_of": organisation},
        headers=headers,
        json=body,
    )


@pytest.mark.asyncio
async def test_a_caller_without_a_did_cannot_publish_for_an_organisation(monkeypatch):
    from src.core.api.routes.okh import get_okh_service

    okh = _okh()
    async with _client(monkeypatch, overrides={get_okh_service: lambda: okh}) as client:
        resp = await _publish(client, "did:key:zOrg")

    assert resp.status_code == 403, resp.text
    assert "personal identity" in resp.text
    assert "later" in resp.text
    okh.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_the_manifests_alias_refuses_the_same_way(monkeypatch):
    from src.core.api.routes.okh import get_okh_service

    okh = _okh()
    async with _client(monkeypatch, overrides={get_okh_service: lambda: okh}) as client:
        resp = await _publish(client, "did:key:zOrg", path="/v1/api/okh/manifests/")

    assert resp.status_code == 403, resp.text
    assert "personal identity" in resp.text
    okh.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_member_without_an_affiliation_cannot_publish_for_the_organisation(
    tmp_path, monkeypatch
):
    from src.core.api.routes.okh import get_okh_service

    service = _auth(tmp_path)
    _ada_row, _admin, space, key = await _ada(service)
    okh = _okh()
    async with _client(
        monkeypatch, service, overrides={get_okh_service: lambda: okh}
    ) as client:
        resp = await _publish(client, space.did, key.token)

    assert resp.status_code == 403, resp.text
    assert "not yet" in resp.text
    assert "later" in resp.text
    okh.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_an_admin_key_is_not_an_affiliation(tmp_path, monkeypatch):
    from src.core.api.routes.okh import get_okh_service

    service = _auth(tmp_path)
    _ada_row, _admin, space, key = await _ada(service, permissions=["admin"])
    okh = _okh()
    async with _client(
        monkeypatch, service, overrides={get_okh_service: lambda: okh}
    ) as client:
        resp = await _publish(client, space.did, key.token)

    assert resp.status_code == 403, resp.text
    assert "not yet" in resp.text
    okh.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_an_expired_affiliation_cannot_publish(tmp_path, monkeypatch):
    from src.core.api.routes.okh import get_okh_service

    service = _auth(tmp_path)
    ada, admin, space, key = await _ada(service)
    await service.issue_grant(
        issuer_did=admin.did,
        subject_did=ada.did,
        permissions=["publish"],
        scope=Scope(kind="space", target=space.did),
        ttl_days=-1,
    )
    okh = _okh()
    async with _client(
        monkeypatch, service, overrides={get_okh_service: lambda: okh}
    ) as client:
        resp = await _publish(client, space.did, key.token)

    assert resp.status_code == 403, resp.text
    assert "not yet" in resp.text
    okh.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_an_affiliated_member_publishes_with_the_evidence_chain(
    tmp_path, monkeypatch
):
    from src.core.api.routes.okh import get_okh_service

    service = _auth(tmp_path)
    ada, admin, space, key = await _ada(service)
    await service.issue_grant(
        issuer_did=admin.did,
        subject_did=ada.did,
        permissions=["publish"],
        scope=Scope(kind="space", target=space.did),
    )
    okh = _okh()
    async with _client(
        monkeypatch, service, overrides={get_okh_service: lambda: okh}
    ) as client:
        resp = await _publish(client, space.did, key.token)

    assert resp.status_code == 201, resp.text
    provenance = okh.create.call_args.kwargs["provenance"]
    assert provenance.on_behalf_of == space.did
    assert provenance.signed_by == ada.did
    assert provenance.signature
    assert provenance.space_claim.space_did == space.did
    assert provenance.space_claim.admin_did == admin.did
    assert provenance.space_claim.signature
    assert provenance.affiliation.issuer_did == admin.did
    assert provenance.affiliation.subject_did == ada.did
    assert "publish" in provenance.affiliation.permissions
    assert provenance.affiliation.signature
    assert "affiliation" not in provenance.signing_payload()


@pytest.mark.asyncio
async def test_a_facility_without_an_affiliation_is_refused_the_same_way(monkeypatch):
    from src.core.api.routes.okw import get_okw_service

    okw = MagicMock()
    okw.create = AsyncMock()
    async with _client(monkeypatch, overrides={get_okw_service: lambda: okw}) as client:
        resp = await client.post(
            "/v1/api/okw/create",
            params={"on_behalf_of": "did:key:zOrg"},
            json={"content": FACILITY},
        )

    assert resp.status_code == 403, resp.text
    assert "personal identity" in resp.text
    assert "later" in resp.text
    okw.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_the_organisation_key_does_not_sign(tmp_path):
    from src.core.models.provenance import RecordProvenance

    service = _auth(tmp_path)
    space = await service.create_identity(uuid4(), IdentityKind.SPACE, "FabLab")
    signed = service.sign_provenance_if_possible(
        RecordProvenance(on_behalf_of=space.did)
    )
    assert signed.signed_by != space.did
    assert not signed.signature


@pytest.mark.asyncio
async def test_a_member_lists_only_their_current_affiliations(tmp_path, monkeypatch):
    service = _auth(tmp_path)
    ada, grace, space, ada_key = await _ada(service)
    grace_key = await service.create_api_key(
        APIKeyCreate(
            name="grace",
            permissions=["write"],
            account_id=UUID(grace.account_id),
        )
    )
    bob = await service.create_identity(uuid4(), IdentityKind.PERSON, "Bob")
    other = await service.create_identity(uuid4(), IdentityKind.SPACE, "Other Shop")
    gone = await service.create_identity(uuid4(), IdentityKind.SPACE, "Gone")
    await service.claim_space(other.did, grace.did)
    await service.claim_space(gone.did, grace.did)
    await service.issue_grant(
        issuer_did=grace.did,
        subject_did=ada.did,
        permissions=["publish"],
        scope=Scope(kind="space", target=space.did),
    )
    await service.issue_grant(
        issuer_did=grace.did,
        subject_did=bob.did,
        permissions=["publish"],
        scope=Scope(kind="space", target=other.did),
    )
    await service.issue_grant(
        issuer_did=grace.did,
        subject_did=ada.did,
        permissions=["publish"],
        scope=Scope(kind="space", target=gone.did),
        ttl_days=-1,
    )
    async with _client(monkeypatch, service) as client:
        ada_resp = await client.get(
            "/v1/api/identity/affiliations",
            headers={"Authorization": f"Bearer {ada_key.token}"},
        )
        grace_resp = await client.get(
            "/v1/api/identity/affiliations",
            headers={"Authorization": f"Bearer {grace_key.token}"},
        )

    assert ada_resp.status_code == 200, ada_resp.text
    rows = ada_resp.json()
    assert [row["display_name"] for row in rows] == ["FabLab"]
    assert rows[0]["space_did"] == space.did
    assert rows[0]["expires_at"]
    assert grace_resp.status_code == 200, grace_resp.text
    assert grace_resp.json() == []


@pytest.mark.asyncio
async def test_a_revoked_affiliation_cannot_publish(tmp_path, monkeypatch):
    from src.core.api.routes.okh import get_okh_service

    service = _auth(tmp_path)
    ada, admin, space, key = await _ada(service)
    grant = await service.issue_grant(
        issuer_did=admin.did,
        subject_did=ada.did,
        permissions=["publish"],
        scope=Scope(kind="space", target=space.did),
    )
    await service.revoke_grant(grant.grant_id)
    okh = _okh()
    async with _client(
        monkeypatch, service, overrides={get_okh_service: lambda: okh}
    ) as client:
        resp = await _publish(client, space.did, key.token)

    assert resp.status_code == 403, resp.text
    assert "not yet" in resp.text
    okh.create.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("organisation", ["FabLab", "did:key:zUnclaimed"])
async def test_free_text_and_an_unclaimed_did_are_refused(
    tmp_path, monkeypatch, organisation
):
    from src.core.api.routes.okh import get_okh_service

    service = _auth(tmp_path)
    _ada_row, _admin, _space, key = await _ada(service)
    okh = _okh()
    async with _client(
        monkeypatch, service, overrides={get_okh_service: lambda: okh}
    ) as client:
        resp = await _publish(client, organisation, key.token)

    assert resp.status_code == 403, resp.text
    assert "not yet" in resp.text
    okh.create.assert_not_awaited()
