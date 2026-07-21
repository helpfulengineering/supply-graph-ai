"""Per-record share / visibility policy (federated-identity Slice 4).

Local publishing policy — who may *pull* a record off this node via the
federation catalog. Lives in its own store (like provenance), never in the
manifest content hash. Not federated: a receiving node decides what to re-share.
"""

from enum import Enum
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
