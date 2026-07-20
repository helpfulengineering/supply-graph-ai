"""Unit tests for IdentityKeyStore + GrantStore (Slice 2)."""

from datetime import datetime, timedelta

import pytest

from src.core.federation.identity import generate_identity, sign_payload
from src.core.models.capability import CapabilityGrant, Scope
from src.core.models.identity import Identity, IdentityKind
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


# --- IdentityKeyStore (node-local filesystem) --------------------------------


def test_identity_key_store_round_trip(tmp_path):
    store = IdentityKeyStore(tmp_path)
    key = generate_identity("Ada")
    identity = Identity(
        did=key.did,
        kind=IdentityKind.PERSON,
        display_name="Ada",
        account_id="acct-1",
    )
    store.save(key, identity)

    loaded_key = store.load_signing_key(key.did)
    assert loaded_key is not None and loaded_key.did == key.did

    loaded_identity = store.load_identity(key.did)
    assert loaded_identity is not None
    assert loaded_identity.kind is IdentityKind.PERSON
    assert loaded_identity.account_id == "acct-1"

    assert store.find_primary_did("acct-1") == key.did
    assert [i.did for i in store.list_identities()] == [key.did]


def test_identity_key_store_writes_only_to_filesystem(tmp_path):
    # The private key must never touch the object store; it lives under
    # <data_dir>/identities/. Assert the file exists on disk.
    store = IdentityKeyStore(tmp_path)
    key = generate_identity("Node")
    store.save(key, Identity(did=key.did, kind=IdentityKind.PERSON, display_name="N"))
    files = list((tmp_path / "identities").glob("*.json"))
    assert len(files) == 1
    assert "private_key_hex" in files[0].read_text("utf-8")


def test_identity_key_store_missing_returns_none(tmp_path):
    store = IdentityKeyStore(tmp_path)
    assert store.load_signing_key("did:key:zMissing") is None
    assert store.load_identity("did:key:zMissing") is None


# --- GrantStore (object store + subject index) -------------------------------


def _signed_grant(issuer, subject_did: str) -> CapabilityGrant:
    grant = CapabilityGrant(
        issuer_did=issuer.did,
        subject_did=subject_did,
        permissions=["write"],
        coarse_floor=["read", "write"],
        scope=Scope(kind="node", target=issuer.did),
        expires_at=datetime.utcnow() + timedelta(days=90),
    )
    grant.signature = sign_payload(issuer.private_key, grant.signing_payload())
    return grant


@pytest.mark.asyncio
async def test_grant_store_save_and_index_by_subject():
    store = GrantStore(_FakeStorageService())
    issuer = generate_identity("issuer")
    g1 = _signed_grant(issuer, "did:key:zSubjectA")
    g2 = _signed_grant(issuer, "did:key:zSubjectA")
    g3 = _signed_grant(issuer, "did:key:zSubjectB")
    for g in (g1, g2, g3):
        await store.save_grant(g)

    a = await store.list_for_subject("did:key:zSubjectA")
    assert {g.grant_id for g in a} == {g1.grant_id, g2.grant_id}
    assert len(await store.list_all()) == 3


@pytest.mark.asyncio
async def test_grant_store_index_rebuild_from_storage():
    backing = _FakeStorageService()
    issuer = generate_identity("issuer")
    grant = _signed_grant(issuer, "did:key:zSubjectA")
    await GrantStore(backing).save_grant(grant)

    # A fresh store must rebuild its index from persisted objects.
    fresh = GrantStore(backing)
    loaded = await fresh.list_for_subject("did:key:zSubjectA")
    assert len(loaded) == 1
    assert loaded[0].grant_id == grant.grant_id
    assert loaded[0].signature == grant.signature


@pytest.mark.asyncio
async def test_grant_store_delete():
    store = GrantStore(_FakeStorageService())
    issuer = generate_identity("issuer")
    grant = _signed_grant(issuer, "did:key:zSubjectA")
    await store.save_grant(grant)
    await store.delete_grant(grant.grant_id)
    assert await store.list_for_subject("did:key:zSubjectA") == []
