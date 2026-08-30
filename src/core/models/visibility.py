"""Per-record share / visibility policy (federated-identity Slice 4).

Local publishing policy — who may *pull* a record off this node via the
federation catalog. Lives in its own store (like provenance), never in the
manifest content hash. Not federated: a receiving node decides what to re-share.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class VisibilityLevel(str, Enum):
    """How far a record may leave this node.

    ``followers`` and ``public`` are both catalog-shareable today (federation
    sync is already follow-gated). ``public`` is reserved for broader registry
    listing later without another migration.
    """

    PRIVATE = "private"
    FOLLOWERS = "followers"
    PUBLIC = "public"


DEFAULT_VISIBILITY = VisibilityLevel.PRIVATE
# Pre-Slice-4 records have no visibility object and were always catalogued;
# treat that absence as followers so existing federation catalogs do not empty.
LEGACY_VISIBILITY = VisibilityLevel.FOLLOWERS


def is_shareable(level: VisibilityLevel | None) -> bool:
    """True iff a record with this visibility may appear in the catalog.

    ``None`` is treated as non-shareable (callers should resolve legacy first).
    """
    if level is None:
        return False
    return level in (VisibilityLevel.FOLLOWERS, VisibilityLevel.PUBLIC)


class VisibilityBody(BaseModel):
    """Request body for PUT …/visibility."""

    visibility: VisibilityLevel = Field(..., description="private | followers | public")


class VisibilityResponse(BaseModel):
    """Visibility for one record."""

    id: UUID
    visibility: VisibilityLevel


@dataclass(frozen=True)
class ViewerScope:
    """Which records one caller may see in a list.

    A viewer sees shareable records plus their own. Ownership keys on the
    subject **DID** — the portable identity that survives to cross-node
    portability — with an account-id fallback for the two populations that have
    no DID: environment-configured API keys, and records written before #403.

    ``dids`` holds the caller's current DID *and* every DID it supersedes, so a
    key rotation does not hide the rotator's own drafts from them.

    An empty scope is anonymous: it owns nothing, and sees only what is
    shareable. Note that ``admin`` grants nothing extra here — an admin's record
    scope is deliberately identical to any other authenticated user's, and
    operators enumerate through the inventory surface instead (ADR §9).
    """

    account_id: Optional[str] = None
    dids: frozenset[str] = frozenset()

    def owns(
        self,
        created_by_did: Optional[str],
        created_by_account: Optional[str],
    ) -> bool:
        """True when this viewer created the record the attribution describes."""
        if created_by_did and created_by_did in self.dids:
            return True
        return bool(
            created_by_account
            and self.account_id
            and created_by_account == self.account_id
        )


ANONYMOUS_SCOPE = ViewerScope()


def visible_to(
    level: Optional[VisibilityLevel],
    viewer: ViewerScope,
    created_by_did: Optional[str],
    created_by_account: Optional[str],
) -> bool:
    """True when ``viewer`` may see a record with this visibility and attribution."""
    return is_shareable(level) or viewer.owns(created_by_did, created_by_account)
