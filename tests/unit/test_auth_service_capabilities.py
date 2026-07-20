"""Unit tests for AuthenticationService identity + capability grants (Slice 2)."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from src.core.federation.identity import generate_identity, sign_payload
from src.core.models.capability import CapabilityGrant, Scope
from src.core.models.identity import IdentityKind
from src.core.services.auth_service import AuthenticationService
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
    svc._grant_store = GrantStore(_FakeStorageService())
    svc._identity_store = IdentityKeyStore(tmp_path)
    # Deterministic trust root: pretend this node's identity is a fresh keypair.
    svc._node_signing = generate_identity("test-node")
    svc._initialized = True
    return svc


def _node_scope(service) -> Scope:
    return Scope(kind="node", target=service._node_signing.did)


@pytest.mark.asyncio
async def test_mint_identity_binds_account(service):
    account_id = uuid4()
    identity = await service.create_identity(account_id, IdentityKind.PERSON, "Ada")
    assert identity.account_id == str(account_id)
    assert service.get_identity(identity.did).did == identity.did
    assert service._identity_store.find_primary_did(str(account_id)) == identity.did


@pytest.mark.asyncio
async def test_node_issued_grant_resolves_to_permissions(service):
    subject = await service.create_identity(uuid4(), IdentityKind.PERSON, "Ada")
    await service.issue_grant(
        issuer_did=service._node_signing.did,
        subject_did=subject.did,
        permissions=["write"],
        scope=_node_scope(service),
        coarse_floor=["read"],
    )
    perms = await service.resolve_capabilities(subject.did, _node_scope(service))
    assert "write" in perms and "read" in perms


@pytest.mark.asyncio
async def test_unknown_scope_kind_denies_all(service):
    subject = await service.create_identity(uuid4(), IdentityKind.PERSON, "Ada")
    weird = Scope(kind="galaxy", target="x")
    await service.issue_grant(
        issuer_did=service._node_signing.did,
        subject_did=subject.did,
        permissions=["write"],
        scope=weird,
        coarse_floor=["read"],
    )
    # Fail closed: even the coarse floor is not honored on an unknown scope kind.
    assert await service.resolve_capabilities(subject.did, weird) == set()


@pytest.mark.asyncio
async def test_expired_grant_is_ignored(service):
    subject = await service.create_identity(uuid4(), IdentityKind.PERSON, "Ada")
    expired = CapabilityGrant(
        issuer_did=service._node_signing.did,
        subject_did=subject.did,
        permissions=["write"],
        coarse_floor=["read"],
        scope=_node_scope(service),
        issued_at=datetime.utcnow() - timedelta(days=10),
        expires_at=datetime.utcnow() - timedelta(days=1),
    )
    expired.signature = sign_payload(
        service._node_signing.private_key, expired.signing_payload()
    )
    await service._grant_store.save_grant(expired)
    assert (
        await service.resolve_capabilities(subject.did, _node_scope(service)) == set()
    )


@pytest.mark.asyncio
async def test_untrusted_issuer_contributes_nothing(service):
    subject = await service.create_identity(uuid4(), IdentityKind.PERSON, "Ada")
    stranger = generate_identity("stranger")
    grant = CapabilityGrant(
        issuer_did=stranger.did,
        subject_did=subject.did,
        permissions=["admin"],
        coarse_floor=["read"],
        scope=_node_scope(service),
        expires_at=datetime.utcnow() + timedelta(days=1),
    )
    grant.signature = sign_payload(stranger.private_key, grant.signing_payload())
    await service._grant_store.save_grant(grant)
    # Valid signature, but issuer is neither the node nor the subject -> untrusted.
    assert (
        await service.resolve_capabilities(subject.did, _node_scope(service)) == set()
    )


@pytest.mark.asyncio
async def test_self_asserted_grant_is_honored_locally(service):
    # Isolated edge bootstrap: an identity issues a grant to itself.
    edge = await service.create_identity(uuid4(), IdentityKind.PERSON, "Edge")
    await service.issue_grant(
        issuer_did=edge.did,
        subject_did=edge.did,
        permissions=["write"],
        scope=Scope(kind="node", target=edge.did),
        coarse_floor=["read"],
    )
    perms = await service.resolve_capabilities(
        edge.did, Scope(kind="node", target=edge.did)
    )
    assert "write" in perms


@pytest.mark.asyncio
async def test_unknown_verb_dropped_but_floor_kept(service):
    subject = await service.create_identity(uuid4(), IdentityKind.PERSON, "Ada")
    await service.issue_grant(
        issuer_did=service._node_signing.did,
        subject_did=subject.did,
        permissions=["telepathy"],  # not a known verb
        scope=_node_scope(service),
        coarse_floor=["read"],
    )
    perms = await service.resolve_capabilities(subject.did, _node_scope(service))
    assert perms == {"read"}  # unknown verb dropped, floor honored


@pytest.mark.asyncio
async def test_revoke_grant_removes_capability(service):
    subject = await service.create_identity(uuid4(), IdentityKind.PERSON, "Ada")
    grant = await service.issue_grant(
        issuer_did=service._node_signing.did,
        subject_did=subject.did,
        permissions=["write"],
        scope=_node_scope(service),
    )
    await service.revoke_grant(grant.grant_id)
    assert (
        await service.resolve_capabilities(subject.did, _node_scope(service)) == set()
    )


@pytest.mark.asyncio
async def test_rotation_links_old_to_new(service):
    subject = await service.create_identity(uuid4(), IdentityKind.PERSON, "Ada")
    rotated = await service.rotate_identity(subject.did)
    assert rotated.did != subject.did
    assert rotated.links_in[-1].from_did == subject.did
    assert rotated.links_in[-1].to_did == rotated.did
    # The rotation link is signed by the OLD key and verifies against it.
    from src.core.federation.identity import verify_payload

    link = rotated.links_in[-1]
    assert verify_payload(subject.did, link.signing_payload(), link.signature)
