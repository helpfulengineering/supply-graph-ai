"""Self-service registration (#403).

A node operator must not be the only way to become someone on a node — that is
what would make one node structurally special rather than merely well-known
(ADR §9). These cover the parts a route contract test cannot: the permission
floor, the mode gate, and that one call produces all three planes.
"""

import pytest
from fastapi import HTTPException

from src.config.security_policy import SecurityMode, get_security_policy
from src.core.federation.identity import generate_identity
from src.core.services.auth_service import AuthenticationService
from src.core.storage.account_storage import AccountStorage
from src.core.storage.auth_storage import AuthStorage
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
    svc._identity_store = IdentityKeyStore(tmp_path)
    svc._node_signing = generate_identity("test-node")
    svc._initialized = True
    return svc


@pytest.mark.asyncio
async def test_registration_mints_account_identity_and_key(service):
    result = await service.register("Ada Lovelace")

    assert result.display_name == "Ada Lovelace"
    assert result.did.startswith("did:key:z")
    # The token exists exactly once, at creation.
    assert result.key.token

    # All three planes agree on the same account.
    accounts = await service.list_accounts()
    assert [a.id for a in accounts] == [result.account_id]
    assert (
        service._identity_store.find_primary_did(str(result.account_id)) == result.did
    )


@pytest.mark.asyncio
async def test_registered_key_never_carries_admin(service):
    result = await service.register("Grace")

    assert set(result.key.permissions) == {"read", "write"}
    assert "admin" not in result.key.permissions


@pytest.mark.asyncio
async def test_registered_key_authenticates_as_its_own_account(service):
    result = await service.register("Katherine")

    user = await service.validate_api_key(result.key.token)
    assert user is not None
    assert user.account_id == result.account_id
    # The DID is resolved from the account binding, which is what record
    # ownership keys on — without it a registrant owns nothing they create.
    assert user.subject_did == result.did


@pytest.mark.asyncio
async def test_shielded_mode_refuses_registration(service, monkeypatch):
    monkeypatch.setattr(
        "src.core.services.auth_service.get_security_policy",
        lambda: get_security_policy(SecurityMode.SHIELDED),
    )

    with pytest.raises(HTTPException) as exc:
        await service.register("Nobody")

    assert exc.value.status_code == 403
    # The message names the mode: an operator hitting this needs to know which
    # posture refused them, not merely that something did.
    assert "shielded" in str(exc.value.detail)
    assert await service.list_accounts() == []
