"""Space-claim store (federated-identity Slice 5).

TOFU admin bindings for space DIDs. Not secret; one claim per space_did.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from ..models.space import SpaceClaim
from .constants import SPACE_CLAIMS_PREFIX, STORAGE_OBJECT_TYPE_SPACE_CLAIM

if TYPE_CHECKING:
    from ..services.storage_service import StorageService

logger = logging.getLogger(__name__)


class SpaceClaimStore:
    """Object-store persistence for space claims, keyed by space_did."""

    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self._prefix = SPACE_CLAIMS_PREFIX
        self._index: Optional[Dict[str, SpaceClaim]] = None

    def _key(self, space_did: str) -> str:
        safe = space_did.replace("/", "_")
        return f"{self._prefix}/{safe}.json"

    async def save(self, claim: SpaceClaim) -> None:
        """Persist a claim (overwrites any prior claim for the same space)."""
        data = json.dumps(claim.model_dump(mode="json")).encode("utf-8")
        await self.storage_service.manager.put_object(
            key=self._key(claim.space_did),
            data=data,
            content_type="application/json",
            metadata={
                "type": STORAGE_OBJECT_TYPE_SPACE_CLAIM,
                "space_did": claim.space_did,
                "admin_did": claim.admin_did,
            },
        )
        if self._index is not None:
            self._index[claim.space_did] = claim

    async def load(self, space_did: str) -> Optional[SpaceClaim]:
        """Load the claim for ``space_did``, or None."""
        await self._ensure_index()
        assert self._index is not None
        return self._index.get(space_did)

    async def list_all(self) -> List[SpaceClaim]:
        """Return every space claim held by this node."""
        await self._ensure_index()
        assert self._index is not None
        return list(self._index.values())

    async def _ensure_index(self) -> None:
        if self._index is not None:
            return
        index: Dict[str, SpaceClaim] = {}
        prefix = f"{self._prefix}/"
        try:
            async for obj in self.storage_service.manager.list_objects(prefix=prefix):
                if "data" in obj:
                    data = obj["data"]
                else:
                    data = await self.storage_service.manager.get_object(obj["key"])
                try:
                    claim = SpaceClaim(**json.loads(data.decode("utf-8")))
                    index[claim.space_did] = claim
                except Exception as e:
                    logger.warning(
                        f"Failed to parse space claim from {obj.get('key')}: {e}"
                    )
        except Exception as e:
            logger.error(f"Failed to build space-claim index: {e}")
            raise
        self._index = index
