"""Unit tests for identity/capability models + signing (Slice 2)."""

from datetime import datetime, timedelta

import pytest

from src.core.federation.identity import (
    canonical_json_bytes,
    generate_identity,
    sign_payload,
    verify_payload,
)
from src.core.models.capability import CapabilityGrant, Scope
from src.core.models.identity import IdentityLink


def _grant(issuer: str, subject: str) -> CapabilityGrant:
    return CapabilityGrant(
        issuer_did=issuer,
        subject_did=subject,
        permissions=["write", "publish"],
        coarse_floor=["read", "write"],
        scope=Scope(kind="node", target=issuer),
        expires_at=datetime.utcnow() + timedelta(days=90),
    )


def test_scope_key_is_stable():
    scope = Scope(kind="pool", target="okh")
    assert scope.key() == "pool:okh:v1"


def test_coarse_floor_must_be_base_subset():
    with pytest.raises(ValueError):
        CapabilityGrant(
            issuer_did="did:key:zA",
            subject_did="did:key:zB",
            permissions=["write"],
            coarse_floor=["publish"],  # not a base permission
            scope=Scope(kind="node", target="did:key:zA"),
            expires_at=datetime.utcnow() + timedelta(days=1),
        )


def test_coarse_floor_allows_domain_permission():
    grant = CapabilityGrant(
        issuer_did="did:key:zA",
        subject_did="did:key:zB",
        permissions=["write"],
        coarse_floor=["read", "domain:manufacturing"],
        scope=Scope(kind="node", target="did:key:zA"),
        expires_at=datetime.utcnow() + timedelta(days=1),
    )
    assert "domain:manufacturing" in grant.coarse_floor


def test_signing_payload_is_deterministic():
    issuer = generate_identity("issuer")
    grant = _grant(issuer.did, "did:key:zSubject")
    assert canonical_json_bytes(grant.signing_payload()) == canonical_json_bytes(
        grant.signing_payload()
    )


def test_grant_sign_and_verify_round_trip():
    issuer = generate_identity("issuer")
    grant = _grant(issuer.did, "did:key:zSubject")
    grant.signature = sign_payload(issuer.private_key, grant.signing_payload())

    assert verify_payload(grant.issuer_did, grant.signing_payload(), grant.signature)


def test_tampered_grant_fails_verification():
    issuer = generate_identity("issuer")
    grant = _grant(issuer.did, "did:key:zSubject")
    grant.signature = sign_payload(issuer.private_key, grant.signing_payload())

    grant.permissions.append("admin")  # tamper after signing
    assert not verify_payload(
        grant.issuer_did, grant.signing_payload(), grant.signature
    )


def test_wrong_issuer_key_fails_verification():
    issuer = generate_identity("issuer")
    attacker = generate_identity("attacker")
    grant = _grant(issuer.did, "did:key:zSubject")
    grant.signature = sign_payload(attacker.private_key, grant.signing_payload())

    assert not verify_payload(
        grant.issuer_did, grant.signing_payload(), grant.signature
    )


def test_identity_link_sign_and_verify():
    old = generate_identity("old")
    new = generate_identity("new")
    link = IdentityLink(
        from_did=old.did,
        to_did=new.did,
        reason="rotation",
        signed_by=old.did,
        signature="",
    )
    link.signature = sign_payload(old.private_key, link.signing_payload())
    assert verify_payload(link.signed_by, link.signing_payload(), link.signature)
