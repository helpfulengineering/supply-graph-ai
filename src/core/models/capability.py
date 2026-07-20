"""Capability grant model — the authorization layer (federated-identity Slice 2).

A ``CapabilityGrant`` is a short-lived, renewable, signed statement:
"issuer_did says subject_did may do <permissions> on <scope> until expires_at."
It is verifiable offline (signature only) and never carries content. See
``notes/federated-identity-adr.md`` §4.2 and the Slice 2 spec.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

# Base permission vocabulary shared with AuthenticationService.check_permission.
# ``domain:<name>`` is also a base permission (prefix-matched). The coarse floor
# of a grant MUST be a subset of this vocabulary so a node that does not
# understand richer verbs still honors a minimum.
BASE_PERMISSIONS = frozenset({"read", "write", "admin"})

# Richer verbs understood by this node beyond the base vocabulary. A grant may
# carry others; unknown verbs are dropped at resolution (the coarse floor is the
# guaranteed minimum), never silently honored.
EXTENDED_PERMISSIONS = frozenset({"publish", "certify", "moderate", "own"})

# Well-known scope kinds. Unknown kinds are stored and relayed but DENIED ALL at
# resolution time (fail closed) — see AuthenticationService.resolve_capabilities.
KNOWN_SCOPE_KINDS = frozenset({"node", "space", "pool", "record"})


def is_base_permission(permission: str) -> bool:
    """True for the base vocabulary (``read``/``write``/``admin``/``domain:x``)."""
    return permission in BASE_PERMISSIONS or permission.startswith("domain:")


def is_known_verb(permission: str) -> bool:
    """True for any permission this node understands (base or extended)."""
    return is_base_permission(permission) or permission in EXTENDED_PERMISSIONS


class Scope(BaseModel):
    """The target a grant applies to. Versioned for forward compatibility."""

    kind: str  # "node" | "space" | "pool" | "record"; unknown -> deny all
    target: str  # node DID | space DID | "okh"/"okw" | content-hash
    v: int = 1

    def key(self) -> str:
        """Stable string form used for scope matching."""
        return f"{self.kind}:{self.target}:v{self.v}"


class CapabilityGrant(BaseModel):
    """A signed, offline-verifiable authorization."""

    grant_id: UUID = Field(default_factory=uuid4)
    issuer_did: str
    subject_did: str
    permissions: List[str] = Field(default_factory=list)
    # Minimum honored even by a node unaware of richer verbs; must be a subset of
    # the base vocabulary.
    coarse_floor: List[str] = Field(default_factory=list)
    scope: Scope
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    not_before: Optional[datetime] = None
    expires_at: datetime
    delegated_from: Optional[UUID] = None  # single-hop for now; chains in Slice 5
    signature: str = ""  # hex; issuer signs signing_payload()

    @field_validator("coarse_floor")
    @classmethod
    def _floor_is_base_subset(cls, value: List[str]) -> List[str]:
        invalid = [p for p in value if not is_base_permission(p)]
        if invalid:
            raise ValueError(
                f"coarse_floor must be a subset of the base permission vocabulary; "
                f"invalid: {invalid}"
            )
        return value

    def signing_payload(self) -> dict:
        """Deterministic, signature-free payload (datetimes as ISO strings)."""
        return {
            "grant_id": str(self.grant_id),
            "issuer_did": self.issuer_did,
            "subject_did": self.subject_did,
            "permissions": list(self.permissions),
            "coarse_floor": list(self.coarse_floor),
            "scope": {
                "kind": self.scope.kind,
                "target": self.scope.target,
                "v": self.scope.v,
            },
            "issued_at": self.issued_at.isoformat(),
            "not_before": self.not_before.isoformat() if self.not_before else None,
            "expires_at": self.expires_at.isoformat(),
            "delegated_from": (
                str(self.delegated_from) if self.delegated_from else None
            ),
        }
