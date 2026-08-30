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


# --- Recovery (#414) --------------------------------------------------------
#
# Without this, a person who registers, closes the tab and did not save the
# token has permanently lost their identity and every private record it made —
# unreachable by everyone, including the operator, because registration collects
# no email, no password and no second factor.


@pytest.mark.asyncio
async def test_registration_issues_a_recovery_code_alongside_the_token(service):
    result = await service.register("Ada")

    assert result.recovery_code
    assert result.recovery_code != result.key.token

    # Stored only as a hash, like the token.
    accounts = await service.list_accounts()
    stored = accounts[0]
    assert stored.recovery_digest
    assert result.recovery_code not in str(stored.model_dump())


@pytest.mark.asyncio
async def test_redeeming_returns_a_key_on_the_same_account_and_did(service):
    registered = await service.register("Ada")

    recovered = await service.redeem_recovery_code(registered.recovery_code)

    assert recovered.account_id == registered.account_id
    assert recovered.did == registered.did, "recovery must not orphan the identity"
    user = await service.validate_api_key(recovered.key.token)
    assert user.account_id == registered.account_id
    # The DID is what record ownership keys on, so this is what makes the
    # account's own private records visible again.
    assert user.subject_did == registered.did


@pytest.mark.asyncio
async def test_redeeming_revokes_the_keys_it_replaces(service):
    """Serves 'it leaked' as well as 'I lost it', so the old key must die."""
    from fastapi import HTTPException

    registered = await service.register("Ada")
    await service.redeem_recovery_code(registered.recovery_code)

    with pytest.raises(HTTPException) as exc:
        await service.validate_api_key(registered.key.token)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_a_code_cannot_be_redeemed_twice(service):
    from fastapi import HTTPException

    registered = await service.register("Ada")
    replacement = await service.redeem_recovery_code(registered.recovery_code)

    with pytest.raises(HTTPException) as exc:
        await service.redeem_recovery_code(registered.recovery_code)
    assert exc.value.status_code == 401

    # ...and the replacement it issued does work.
    again = await service.redeem_recovery_code(replacement.recovery_code)
    assert again.account_id == registered.account_id


@pytest.mark.asyncio
async def test_a_recovered_key_never_carries_admin(service):
    """A way back in, never a way up — whatever the account held before."""
    registered = await service.register("Ada")
    keys = await service._auth_storage.list_keys()
    promoted = keys[0]
    promoted.permissions = ["read", "write", "admin"]
    await service._auth_storage.save_key(promoted)

    recovered = await service.redeem_recovery_code(registered.recovery_code)
    assert "admin" not in recovered.key.permissions


@pytest.mark.asyncio
async def test_an_unknown_code_is_refused_without_naming_an_account(service):
    from fastapi import HTTPException

    await service.register("Ada")

    with pytest.raises(HTTPException) as exc:
        await service.redeem_recovery_code("not-a-real-code")
    assert exc.value.status_code == 401
    assert "Ada" not in str(exc.value.detail)


@pytest.mark.asyncio
async def test_an_index_pointer_alone_cannot_take_over_an_account(service):
    """Verification reads the digest off the account record, not off the index
    that found it — the same rule that keeps a written index entry from being
    an authentication bypass for API keys."""
    import json

    from fastapi import HTTPException

    victim = await service.register("Victim")
    attacker_code = "attacker-chosen-value"
    storage = service._account_storage
    await storage.storage_service.manager.put_object(
        storage._recovery_index_key(service._token_digest(attacker_code)),
        json.dumps({"account_id": str(victim.account_id)}).encode("utf-8"),
    )

    with pytest.raises(HTTPException) as exc:
        await service.redeem_recovery_code(attacker_code)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_shielded_mode_refuses_recovery_and_names_the_mode(service, monkeypatch):
    registered = await service.register("Ada")
    monkeypatch.setattr(
        "src.core.services.auth_service.get_security_policy",
        lambda: get_security_policy(SecurityMode.SHIELDED),
    )

    with pytest.raises(HTTPException) as exc:
        await service.redeem_recovery_code(registered.recovery_code)
    assert exc.value.status_code == 403
    assert "shielded" in str(exc.value.detail)
