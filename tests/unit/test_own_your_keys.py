"""A person manages the keys on their own account (#413).

Before this the entire identity surface except whoami and the public policy was
admin-only, so someone who registered got one key forever: no second key for
another device, and no way to kill one that leaked. That is an odd position for
a system whose premise is that identity is self-sovereign, and it meant a leaked
token stayed valid indefinitely, because self-service keys also never expired.

Scoping mirrors #403's record scoping: the same endpoint, a viewer-dependent
result, and an admin's node-wide view unchanged.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.config.security_policy import get_security_policy
from src.core.models.account import AccountCreate
from src.core.models.auth import APIKeyCreate, AuthenticatedUser
from src.core.services.auth_service import AuthenticationService
from src.core.storage.account_storage import AccountStorage
from src.core.federation.identity import generate_identity
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
    # register() mints a person DID, so the identity store has to be real here.
    svc._identity_store = IdentityKeyStore(tmp_path)
    svc._node_signing = generate_identity("test-node")
    svc._initialized = True
    return svc


async def _person(service, name: str):
    """An account with one key, and the AuthenticatedUser that key resolves to."""
    account = await service.create_account(AccountCreate(display_name=name))
    created = await service.create_api_key(
        APIKeyCreate(
            name=f"{name}-key", permissions=["read", "write"], account_id=account.id
        )
    )
    user = await service.validate_api_key(created.token)
    return account, user, created


@pytest.mark.asyncio
async def test_you_see_your_own_keys_and_not_anyone_elses(service):
    _, ada, _ = await _person(service, "ada")
    _, bob, bob_key = await _person(service, "bob")

    ada_view = await service.list_api_keys_for(ada)
    assert {k.name for k in ada_view} == {"ada-key"}
    assert bob_key.key_id not in {k.key_id for k in ada_view}


@pytest.mark.asyncio
async def test_an_admin_still_sees_the_whole_node(service):
    await _person(service, "ada")
    await _person(service, "bob")
    admin = AuthenticatedUser(
        key_id=uuid4(), name="admin", permissions=["read", "write", "admin"]
    )

    assert len(await service.list_api_keys_for(admin)) == 2


@pytest.mark.asyncio
async def test_someone_elses_key_is_refused_as_if_it_did_not_exist(service):
    """Otherwise the error is an oracle for which key ids are real."""
    _, ada, _ = await _person(service, "ada")
    _, _, bob_key = await _person(service, "bob")

    with pytest.raises(HTTPException) as theirs:
        await service.revoke_api_key_for(ada, bob_key.key_id)
    with pytest.raises(HTTPException) as absent:
        await service.revoke_api_key_for(ada, uuid4())

    assert theirs.value.status_code == absent.value.status_code == 404
    assert str(theirs.value.detail) == str(absent.value.detail)


@pytest.mark.asyncio
async def test_you_can_revoke_your_own_key(service):
    _, ada, key = await _person(service, "ada")
    await service.revoke_api_key_for(ada, key.key_id)

    stored = await service._auth_storage.load_key(key.key_id)
    assert stored.revoked is True


@pytest.mark.asyncio
async def test_revoke_others_leaves_you_signed_in(service):
    """The panic case — and locking yourself out while doing it would be a
    remarkable way to answer it."""
    account, ada, current = await _person(service, "ada")
    for i in range(3):
        await service.create_api_key(
            APIKeyCreate(name=f"extra-{i}", permissions=["read"], account_id=account.id)
        )

    revoked = await service.revoke_other_keys(ada)

    assert revoked == 3
    still_valid = await service.validate_api_key(current.token)
    assert still_valid.key_id == current.key_id
    remaining = [k for k in await service.list_api_keys_for(ada) if not k.revoked]
    assert [k.key_id for k in remaining] == [current.key_id]


@pytest.mark.asyncio
async def test_revoke_others_does_not_reach_another_account(service):
    account, ada, _ = await _person(service, "ada")
    _, bob, bob_key = await _person(service, "bob")

    await service.revoke_other_keys(ada)

    assert (await service._auth_storage.load_key(bob_key.key_id)).revoked is False


@pytest.mark.asyncio
async def test_a_self_service_key_expires(service):
    """An abandoned key has to stop working on its own; the ADR's
    revocation-by-expiry covered grants but not the credential doing the work."""
    result = await service.register("Ada")
    stored = (await service._auth_storage.list_keys())[0]

    assert stored.expires_at is not None
    expected = datetime.utcnow() + timedelta(days=get_security_policy().key_ttl_days)
    assert abs((stored.expires_at - expected).total_seconds()) < 60
    assert result.key.token


@pytest.mark.asyncio
async def test_an_expired_key_says_so_rather_than_that_it_is_invalid(service):
    _, _, key = await _person(service, "ada")
    stored = await service._auth_storage.load_key(key.key_id)
    stored.expires_at = datetime.utcnow() - timedelta(days=1)
    await service._auth_storage.save_key(stored)

    with pytest.raises(HTTPException) as exc:
        await service.validate_api_key(key.token)
    assert exc.value.status_code == 401
    assert "expired" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_renewal_keeps_the_same_token(service):
    """Otherwise it is not renewal, it is replacement — and everywhere the
    token is already stored would have to be updated."""
    _, ada, key = await _person(service, "ada")
    stored = await service._auth_storage.load_key(key.key_id)
    stored.expires_at = datetime.utcnow() + timedelta(days=1)
    await service._auth_storage.save_key(stored)

    renewed = await service.renew_api_key(ada, key.key_id)

    assert renewed.expires_at > datetime.utcnow() + timedelta(days=2)
    assert renewed.token is None, "renewal must not re-issue a token"
    assert (await service.validate_api_key(key.token)).key_id == key.key_id


@pytest.mark.asyncio
async def test_you_cannot_renew_someone_elses_key_or_a_revoked_one(service):
    _, ada, ada_key = await _person(service, "ada")
    _, _, bob_key = await _person(service, "bob")

    with pytest.raises(HTTPException) as other:
        await service.renew_api_key(ada, bob_key.key_id)
    assert other.value.status_code == 404

    await service.revoke_api_key_for(ada, ada_key.key_id)
    with pytest.raises(HTTPException) as revoked:
        await service.renew_api_key(ada, ada_key.key_id)
    assert revoked.value.status_code == 409
