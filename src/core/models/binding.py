"""Online identity bindings (federated-identity Slice 7).

Bindings are an *optional* convenience/attestation layer atop self-sovereign
``did:key`` identities. Domain and OAuth bindings are additive evidence — they
are never required for offline operation. See ``notes/federated-identity-adr.md``
§6 (org-claim) and Slice 7.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class IdentityBinding(BaseModel):
    """Signed claim that ``subject_did`` controls an external identifier."""

    binding_id: UUID = Field(default_factory=uuid4)
    subject_did: str
    kind: str  # "domain" | "oauth" | forward-compatible
    # Typed external id, e.g. "domain:example.org", "oauth:github:12345"
    external_id: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    challenge: Optional[str] = None  # domain bind challenge (cleared after verify)
    verified: bool = False
    verified_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    signature: str = ""  # hex; subject DID signs signing_payload()

    def signing_payload(self) -> dict:
        """Deterministic, signature-free payload (excludes challenge)."""
        return {
            "binding_id": str(self.binding_id),
            "subject_did": self.subject_did,
            "kind": self.kind,
            "external_id": self.external_id,
            "evidence": self.evidence,
            "verified": self.verified,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "created_at": self.created_at.isoformat(),
        }


class DomainBindRequest(BaseModel):
    """Start a domain (``.well-known``) binding for a DID."""

    subject_did: str
    domain: str  # e.g. "example.org" (no scheme)


class DomainBindStartResponse(BaseModel):
    """Pending domain bind plus the document the operator must host."""

    binding: IdentityBinding
    well_known_url: str
    well_known_document: Dict[str, Any]


class DomainVerifyRequest(BaseModel):
    """Complete a pending domain binding by fetching ``.well-known``."""

    subject_did: str
    domain: str


class OAuthBindRequest(BaseModel):
    """Record an OAuth/OIDC external-subject binding (post-IdP verification).

    The OAuth redirect dance lives in the frontend/IdP; this API stores the
    resulting binding once claims are verified out-of-band.
    """

    subject_did: str
    provider: str  # e.g. "github", "google", "orcid"
    external_subject: str  # IdP subject / username
    evidence: Dict[str, Any] = Field(default_factory=dict)
    # When True (default), mark verified — caller asserts IdP proof already checked.
    verified: bool = True


class DirectoryEntry(BaseModel):
    """Trust-on-follow directory row (peacetime registry posture)."""

    did: str
    display_name: str = ""
    base_url: Optional[str] = None
    domain: Optional[str] = None
    verified_bindings: List[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DirectoryPublishRequest(BaseModel):
    """Publish or refresh this node's directory entry."""

    did: str
    display_name: str = ""
    base_url: Optional[str] = None
    domain: Optional[str] = None


def domain_external_id(domain: str) -> str:
    """Normalize a host to the binding external_id form."""
    host = domain.strip().lower()
    for prefix in ("https://", "http://"):
        if host.startswith(prefix):
            host = host[len(prefix) :]
    host = host.rstrip("/").split("/")[0]
    return f"domain:{host}"


def oauth_external_id(provider: str, external_subject: str) -> str:
    """Normalize provider + subject to the binding external_id form."""
    return f"oauth:{provider.strip().lower()}:{external_subject.strip()}"


def well_known_url(domain: str) -> str:
    """HTTPS URL for the OHM DID well-known document."""
    host = domain_external_id(domain).removeprefix("domain:")
    return f"https://{host}/.well-known/ohm-did.json"


def well_known_document(did: str, challenge: str) -> Dict[str, Any]:
    """Document an operator should host at ``.well-known/ohm-did.json``."""
    return {
        "did": did,
        "challenge": challenge,
        "method": "ohm-domain-bind-v1",
    }
