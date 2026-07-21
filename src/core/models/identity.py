"""Self-sovereign identity model (federated-identity Slice 2).

An ``Identity`` is a permanent, rotatable Ed25519 ``did:key`` bound to a person,
space, or node. Rotation and custodial handoff are recorded as signed
``IdentityLink`` edges so reputation follows the chain, not a single key. See
``notes/federated-identity-adr.md`` §4.1.
"""

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class IdentityKind(str, Enum):
    """What an identity represents."""

    PERSON = "person"
    SPACE = "space"
    NODE = "node"


class IdentityLink(BaseModel):
    """A signed statement linking one DID to another (rotation / handoff)."""

    from_did: str
    to_did: str
    reason: Literal["rotation", "custodial_handoff", "reissue"]
    signed_by: str  # DID that authorized the link (old key, custodian, or admin)
    signature: str  # hex over signing_payload()
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def signing_payload(self) -> dict:
        """Deterministic, signature-free payload."""
        return {
            "from_did": self.from_did,
            "to_did": self.to_did,
            "reason": self.reason,
            "signed_by": self.signed_by,
            "created_at": self.created_at.isoformat(),
        }


class Identity(BaseModel):
    """The public record for a DID (private key lives in the node-local store)."""

    did: str  # did:key:z... (Ed25519)
    kind: IdentityKind
    display_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Owning account (custodial binding); a person account has one primary DID.
    account_id: Optional[str] = None
    # Prior DIDs this identity supersedes/absorbs (walked for reputation).
    links_in: List[IdentityLink] = Field(default_factory=list)
    custodial: bool = False


class IdentityMint(BaseModel):
    """Request payload for minting an identity bound to an account."""

    account_id: UUID
    kind: IdentityKind = IdentityKind.PERSON
    display_name: str = ""
