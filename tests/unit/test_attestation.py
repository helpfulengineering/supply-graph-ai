"""Unit tests for attestations + bundle_hash (Slice 6)."""

from uuid import uuid4

import pytest

from src.core.federation.identity import generate_identity
from src.core.federation.merkle import merkle_root
from src.core.models.attestation import (
    Attestation,
    verify_attestation,
)
from src.core.models.identity import IdentityKind
from src.core.packaging.pin import bundle_hash
from src.core.services.auth_service import AuthenticationService
from src.core.storage.attestation_store import AttestationStore
from src.core.storage.grant_store import GrantStore
from src.core.storage.identity_key_store import IdentityKeyStore
from src.core.storage.space_claim_store import SpaceClaimStore


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
    backing = _FakeStorageService()
    svc = AuthenticationService()
    svc._grant_store = GrantStore(backing)
    svc._space_claim_store = SpaceClaimStore(backing)
    svc._attestation_store = AttestationStore(backing)
    svc._identity_store = IdentityKeyStore(tmp_path)
    svc._node_signing = generate_identity("test-node")
    svc._initialized = True
    return svc


def test_bundle_hash_is_merkle_over_manifest_and_sorted_files():
    pin = {
        "manifest_content_hash": "sha256:aaaa",
        "file_hashes": {
            "b.txt": "bbbb",
            "a.txt": "aaaa",
        },
    }
    expected = f"sha256:{merkle_root(['sha256:aaaa', 'aaaa', 'bbbb'])}"
    assert bundle_hash(pin) == expected


def test_verify_attestation_roundtrip():
    issuer = generate_identity("Issuer")
    att = Attestation(
        type="vouch",
        issuer_did=issuer.did,
        subject_did="did:key:zSubject",
        claim={"note": "trusted"},
    )
    from src.core.federation.identity import sign_payload

    att.signature = sign_payload(issuer.private_key, att.signing_payload())
    assert verify_attestation(att)
    att.claim["note"] = "tampered"
    assert not verify_attestation(att)


@pytest.mark.asyncio
async def test_issue_and_list_attestation(service):
    person = await service.create_identity(uuid4(), IdentityKind.PERSON, "Ada")
    att = await service.issue_attestation(
        type="authored",
        subject_did=person.did,
        content_hash="sha256:design",
    )
    assert att.signature
    assert verify_attestation(att)

    listed = await service.list_attestations(subject_did=person.did)
    assert len(listed) == 1
    assert listed[0].attestation_id == att.attestation_id


@pytest.mark.asyncio
async def test_certify_binds_bundle_and_rides_catalog(service):
    firm = await service.create_identity(uuid4(), IdentityKind.SPACE, "Firm")
    att = await service.certify(
        subject_did=firm.did,
        bundle_hash="sha256:bundle",
        version="1.2.0",
        manifest_content_hash="sha256:manifest",
    )
    assert att.type == "certified"
    assert att.content_hash == "sha256:bundle"
    assert att.claim["version"] == "1.2.0"
    assert att.claim["manifest_content_hash"] == "sha256:manifest"
    assert verify_attestation(att)

    for_catalog = await service.list_attestations_for_catalog("sha256:manifest")
    assert len(for_catalog) == 1


@pytest.mark.asyncio
async def test_list_reputation_filters_unknown_and_invalid(service):
    person = await service.create_identity(uuid4(), IdentityKind.PERSON, "Ada")
    await service.issue_attestation(type="vouch", subject_did=person.did)
    await service.issue_attestation(type="future-unknown-type", subject_did=person.did)

    # Persist an invalid signature under a known type.
    bad = Attestation(
        type="certified",
        issuer_did=person.did,
        subject_did=person.did,
        content_hash="sha256:x",
        claim={"version": "0"},
        signature="00" * 64,
    )
    await service.save_attestation(bad)

    rep = await service.list_reputation(person.did)
    assert len(rep) == 1
    assert rep[0].type == "vouch"


@pytest.mark.asyncio
async def test_issue_requires_held_issuer_key(service):
    with pytest.raises(Exception) as exc:
        await service.issue_attestation(
            type="vouch",
            subject_did="did:key:zSubject",
            issuer_did="did:key:zNotHeld",
        )
    assert getattr(exc.value, "status_code", None) == 403
