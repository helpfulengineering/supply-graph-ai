"""A coordinator mints invites without being an admin (#573)."""

from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from src.core.federation.identity import generate_identity
from src.core.models.auth import APIKeyCreate, AuthenticatedUser
from src.core.models.identity import IdentityKind
from src.core.services.auth_service import AuthenticationService
from src.core.storage.account_storage import AccountStorage
from src.core.storage.auth_storage import AuthStorage
from src.core.storage.grant_store import GrantStore
from src.core.storage.identity_key_store import IdentityKeyStore


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


@pytest.fixture
def service(tmp_path) -> AuthenticationService:
    svc = AuthenticationService()
    storage = _FakeStorageService()
    svc._auth_storage = AuthStorage(storage)
    svc._account_storage = AccountStorage(storage)
    svc._grant_store = GrantStore(storage)
    svc._identity_store = IdentityKeyStore(tmp_path)
    svc._node_signing = generate_identity("test-node")
    svc._initialized = True
    return svc


async def _member_key(service, name: str):
    account_id = uuid4()
    identity = await service.create_identity(account_id, IdentityKind.PERSON, name)
    key = await service.create_api_key(
        APIKeyCreate(
            name=name,
            permissions=["read", "write"],
            account_id=account_id,
        )
    )
    return identity, key


async def _coordinator(service, name: str):
    identity, key = await _member_key(service, name)
    await service.issue_coordinate_grant(identity.did)
    return identity, key


@asynccontextmanager
async def _client(service, monkeypatch, overrides=None):
    """The real routes, against this service rather than the process singleton.

    ``require_coordinate`` calls ``AuthenticationService.get_instance()``, not
    the ``get_auth_service`` dependency a test can override.
    """

    async def get_instance(cls):
        return service

    monkeypatch.setattr(
        AuthenticationService, "get_instance", classmethod(get_instance)
    )
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
        for dependency in overrides or {}:
            api_v1.dependency_overrides.pop(dependency, None)


@pytest.mark.asyncio
async def test_a_coordinator_can_mint_an_invite_and_a_member_cannot(
    service, monkeypatch
):
    _ada, ada_key = await _coordinator(service, "Ada")
    _grace, grace_key = await _member_key(service, "Grace")

    async with _client(service, monkeypatch) as client:
        minted = await client.post(
            "/v1/api/identity/invites",
            headers={"Authorization": f"Bearer {ada_key.token}"},
            json={"ttl_days": 7},
        )
        refused = await client.post(
            "/v1/api/identity/invites",
            headers={"Authorization": f"Bearer {grace_key.token}"},
            json={"ttl_days": 7},
        )

    assert minted.status_code == 201, minted.text
    assert minted.json()["token"]
    assert refused.status_code == 403


@pytest.mark.asyncio
async def test_a_coordinator_can_list_and_revoke_an_invite(service, monkeypatch):
    _ada, ada_key = await _coordinator(service, "Ada")
    _grace, grace_key = await _member_key(service, "Grace")
    invite = await service.mint_invite(ttl_days=7)

    async with _client(service, monkeypatch) as client:
        listed = await client.get(
            "/v1/api/identity/invites",
            headers={"Authorization": f"Bearer {ada_key.token}"},
        )
        grace_listed = await client.get(
            "/v1/api/identity/invites",
            headers={"Authorization": f"Bearer {grace_key.token}"},
        )
        revoked = await client.post(
            f"/v1/api/identity/invites/{invite.invite_id}/revoke",
            headers={"Authorization": f"Bearer {ada_key.token}"},
        )

    assert listed.status_code == 200, listed.text
    assert listed.json()[0]["invite_id"] == str(invite.invite_id)
    assert "token" not in listed.json()[0]
    assert grace_listed.status_code == 403
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["revoked"] is True


@pytest.mark.asyncio
async def test_a_coordinator_cannot_reconfigure_the_node(service, monkeypatch):
    _ada, ada_key = await _coordinator(service, "Ada")
    headers = {"Authorization": f"Bearer {ada_key.token}"}

    async with _client(service, monkeypatch) as client:
        registration = await client.put(
            "/v1/api/identity/registration",
            headers=headers,
            json={"registration": "closed"},
        )
        storage = await client.get("/v1/api/storage/config", headers=headers)
        llm = await client.get("/v1/api/llm/credentials", headers=headers)

    assert registration.status_code == 403
    assert storage.status_code == 403
    assert llm.status_code == 403


@pytest.mark.asyncio
async def test_member_inventory_names_people_and_their_facilities(service):
    from src.core.models.account import AccountCreate

    ada = await service.create_account(AccountCreate(display_name="Ada Lovelace"))
    await service._account_storage.claim_username(ada, "ada")
    grace = await service.create_account(AccountCreate(display_name="Grace"))
    await service._account_storage.claim_username(grace, "grace")

    rows = await service.member_inventory(
        [
            {
                "created_by_account": str(ada.id),
                "name": "Ada's printer",
                "processes": ["3D Printing"],
                "visibility": "members",
            }
        ]
    )

    ada_row = next(row for row in rows if row["username"] == "ada")
    assert ada_row["display_name"] == "Ada Lovelace"
    assert ada_row["facilities"] == [
        {
            "name": "Ada's printer",
            "processes": ["3D Printing"],
            "visibility": "members",
        }
    ]
    grace_row = next(row for row in rows if row["username"] == "grace")
    assert grace_row["facilities"] == []
    assert set(ada_row) == {"username", "display_name", "facilities"}


@pytest.mark.asyncio
async def test_a_facility_reaches_the_inventory_as_name_processes_and_visibility():
    import json

    from src.core.services.base import ServiceStatus
    from src.core.services.okw_service import OKWService

    facility_id = str(uuid4())
    account_id = str(uuid4())
    storage = _FakeStorageService()
    await storage.manager.put_object(
        key=f"okw/{facility_id}.json",
        data=json.dumps(
            {
                "id": facility_id,
                "name": "Ada's printer",
                "manufacturing_processes": ["3D Printing"],
                "description": "in the spare room",
                "ohm_created_by": account_id,
            }
        ).encode(),
        content_type="application/json",
    )
    svc = OKWService()
    svc.storage = storage
    svc.status = ServiceStatus.ACTIVE

    rows = await svc.coordinator_facilities()

    assert rows == [
        {
            "created_by_account": account_id,
            "name": "Ada's printer",
            "processes": ["3D Printing"],
            "visibility": "followers",
        }
    ]


@pytest.mark.asyncio
async def test_a_coordinator_sees_the_member_inventory_and_a_member_does_not(
    service, monkeypatch
):
    from src.core.api.routes.identity import member_facilities
    from src.core.models.account import AccountCreate

    _ada, ada_key = await _coordinator(service, "Ada")
    _grace_identity, grace_key = await _member_key(service, "Grace")
    grace = await service.create_account(AccountCreate(display_name="Grace Hopper"))
    await service._account_storage.claim_username(grace, "grace")

    async def facilities():
        return [
            {
                "created_by_account": str(grace.id),
                "name": "Grace's printer",
                "processes": ["Laser Cutting"],
                "visibility": "members",
            }
        ]

    async with _client(service, monkeypatch, {member_facilities: facilities}) as client:
        seen = await client.get(
            "/v1/api/identity/members",
            headers={"Authorization": f"Bearer {ada_key.token}"},
        )
        refused = await client.get(
            "/v1/api/identity/members",
            headers={"Authorization": f"Bearer {grace_key.token}"},
        )

    assert seen.status_code == 200, seen.text
    grace_row = next(row for row in seen.json() if row["username"] == "grace")
    assert grace_row["display_name"] == "Grace Hopper"
    assert grace_row["facilities"] == [
        {
            "name": "Grace's printer",
            "processes": ["Laser Cutting"],
            "visibility": "members",
        }
    ]
    assert refused.status_code == 403


@pytest.mark.asyncio
async def test_an_admin_issues_a_coordinate_grant_on_this_node(service, monkeypatch):
    subject = await service.create_identity(uuid4(), IdentityKind.PERSON, "Ada")
    admin_key = await service.create_api_key(
        APIKeyCreate(name="admin", permissions=["admin"])
    )
    _member, member_key = await _member_key(service, "Grace")

    async with _client(service, monkeypatch) as client:
        issued = await client.post(
            "/v1/api/identity/coordinate",
            headers={"Authorization": f"Bearer {admin_key.token}"},
            json={"subject_did": subject.did},
        )
        refused = await client.post(
            "/v1/api/identity/coordinate",
            headers={"Authorization": f"Bearer {member_key.token}"},
            json={"subject_did": subject.did},
        )

    assert issued.status_code == 201, issued.text
    body = issued.json()
    assert body["permissions"] == ["coordinate"]
    assert body["scope"]["kind"] == "node"
    assert body["scope"]["target"] == service._node_signing.did
    assert "expires_at" in body
    assert refused.status_code == 403


@pytest.mark.asyncio
async def test_whoami_names_a_coordinator_without_making_them_admin(
    service, monkeypatch
):
    _ada, ada_key = await _coordinator(service, "Ada")

    async with _client(service, monkeypatch) as client:
        me = await client.get(
            "/v1/api/identity/whoami",
            headers={"Authorization": f"Bearer {ada_key.token}"},
        )

    assert me.status_code == 200, me.text
    body = me.json()
    assert "coordinate" in body["capabilities"]
    assert "admin" not in body["permissions"]
    assert "admin" not in body["capabilities"]


def test_a_coordinator_sees_the_same_records_as_a_member(service):
    account_id = uuid4()
    member = AuthenticatedUser(
        key_id=uuid4(),
        name="ada",
        permissions=["read", "write"],
        account_id=account_id,
        subject_did="did:key:z6MkAda",
    )
    coordinator = member.model_copy(
        update={"permissions": ["read", "write", "coordinate"]}
    )

    assert service.viewer_scope(member) == service.viewer_scope(coordinator)
