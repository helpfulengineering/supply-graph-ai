"""What an operator may see without reading a record (#405).

An admin's record scope is identical to any other user's — they do not read
private records (ADR §9). This is the replacement: every operator task needs to
*enumerate*, not to read. Storage migration and orphan cleanup need ids and
sizes; support needs an owner and a visibility; takedown needs an id and a
delete.

Nothing here is derived from manifest content. No body, and deliberately no
title or description either: a title states intent, which is most of what a
private draft is.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from ..base import SuccessResponse


class InventoryRow(BaseModel):
    """One record, described by its metadata only."""

    id: str
    #: The creator's subject DID, which is what ownership keys on. ``None`` for
    #: records written before per-viewer scoping, and for env-key callers.
    created_by_did: Optional[str] = None
    #: The owning account id. The fallback identifier where no DID exists.
    created_by_account: Optional[str] = None
    #: How far this record may travel — private, followers, public.
    visibility: str
    #: Bytes on the object store. What a migration needs to plan, and what
    #: makes an orphan or a runaway upload visible.
    size_bytes: Optional[int] = None
    #: Last write, ISO 8601. ``None`` when the backend does not report one.
    modified_at: Optional[str] = None


class InventoryData(BaseModel):
    """A page of rows, plus what the operator needs to reason about the whole."""

    rows: List[InventoryRow] = Field(default_factory=list)
    #: Total across the node, not just this page.
    total: int
    #: How many of the total are not shareable — the ones only their owner can
    #: see, and therefore the ones this surface exists to make accountable.
    private_total: int


class InventoryResponse(SuccessResponse):
    """Envelope for an inventory listing."""

    data: InventoryData
