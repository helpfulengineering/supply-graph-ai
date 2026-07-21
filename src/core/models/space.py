"""Space claim model (federated-identity Slice 5).

A space is an :class:`~src.core.models.identity.Identity` with
``kind=SPACE``. A :class:`SpaceClaim` is the TOFU binding of a person DID as
that space's admin — signed by the *space* key so the claim is offline-verifiable.
Domain binding (``did:web`` / ``.well-known``) is reserved for a later slice.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SpaceClaim(BaseModel):
    """Signed statement: ``admin_did`` administers ``space_did``."""

    space_did: str
    admin_did: str
    claimed_at: datetime = Field(default_factory=datetime.utcnow)
    claim_method: Literal["tofu"] = "tofu"
    signature: str = ""  # hex; space key signs signing_payload()

    def signing_payload(self) -> dict:
        """Deterministic, signature-free payload."""
        return {
            "space_did": self.space_did,
            "admin_did": self.admin_did,
            "claimed_at": self.claimed_at.isoformat(),
            "claim_method": self.claim_method,
        }


class SpaceClaimRequest(BaseModel):
    """Request payload for claiming a space (TOFU admin bind)."""

    space_did: str
    admin_did: str
