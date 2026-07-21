"""Durable attestations (federated-identity Slice 6).

An attestation is a signed, backward-looking *fact* about a subject (and
optionally a content hash). Unlike capability grants, attestations do not expire
by default and are the substrate for reputation. ``type`` is an open string with
well-known constants — unknown types are stored and relayed, but ignored by
reputation helpers until understood. See ``notes/federated-identity-adr.md`` §4.3.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# Well-known attestation types. Open set — unknown types are stored/relayed.
KNOWN_ATTESTATION_TYPES = frozenset(
    {
        "authored",
        "published",
        "on_behalf_of",
        "certified",
        "vouch",
        "space_member",
        "listed",
        "curated",
        "domain_bound",
        "oauth_bound",
    }
)


class Attestation(BaseModel):
    """A signed, durable fact about a subject."""

    attestation_id: UUID = Field(default_factory=uuid4)
    type: str  # well-known constant or forward-compatible extension
    issuer_did: str
    subject_did: str
    content_hash: Optional[str] = None  # sha256:... / bundle hash when about content
    claim: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None  # usually None (durable)
    signature: str = ""  # hex; issuer signs signing_payload()

    def signing_payload(self) -> dict:
        """Deterministic, signature-free payload."""
        return {
            "attestation_id": str(self.attestation_id),
            "type": self.type,
            "issuer_did": self.issuer_did,
            "subject_did": self.subject_did,
            "content_hash": self.content_hash,
            "claim": self.claim,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class AttestationIssue(BaseModel):
    """Request payload for issuing an attestation."""

    type: str
    subject_did: str
    issuer_did: Optional[str] = None  # defaults to local node identity
    content_hash: Optional[str] = None
    claim: Dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None


class CertifyRequest(BaseModel):
    """Request payload for a ``certified`` attestation over a bundle hash."""

    subject_did: str  # firm / space DID standing behind the release
    bundle_hash: str
    version: str
    issuer_did: Optional[str] = None
    # When set, stored in claim so the attestation rides the matching catalog record.
    manifest_content_hash: Optional[str] = None
    claim: Dict[str, Any] = Field(default_factory=dict)


def verify_attestation(attestation: Attestation) -> bool:
    """True iff the attestation signature verifies offline (and is in-window)."""
    from ..federation.identity import verify_payload

    if not attestation.signature or not attestation.issuer_did:
        return False
    if attestation.expires_at is not None:
        if datetime.utcnow() >= attestation.expires_at:
            return False
    return verify_payload(
        attestation.issuer_did,
        attestation.signing_payload(),
        attestation.signature,
    )
