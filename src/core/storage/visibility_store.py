"""Per-record visibility store (federated-identity Slice 4).

Local publishing policy keyed by record id, kept out of the design content hash.
Same plane pattern as :class:`ProvenanceStore`.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Optional

from ..models.visibility import VisibilityLevel
from .constants import STORAGE_OBJECT_TYPE_VISIBILITY, VISIBILITY_PREFIX

if TYPE_CHECKING:
    from ..services.storage_service import StorageService

logger = logging.getLogger(__name__)


class VisibilityStore:
    """Object-store persistence for record visibility, keyed by record id."""

    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self._prefix = VISIBILITY_PREFIX

    def _key(self, record_id: str) -> str:
        return f"{self._prefix}/{record_id}.json"

    async def save(self, record_id: str, level: VisibilityLevel) -> None:
        """Persist visibility for a record."""
        data = json.dumps({"visibility": level.value}).encode("utf-8")
        await self.storage_service.manager.put_object(
            key=self._key(record_id),
            data=data,
            content_type="application/json",
            metadata={
                "type": STORAGE_OBJECT_TYPE_VISIBILITY,
                "record_id": record_id,
            },
        )

    async def load(self, record_id: str) -> Optional[VisibilityLevel]:
        """Load visibility for a record, or None if absent/unreadable."""
        try:
            data = await self.storage_service.manager.get_object(self._key(record_id))
            raw = json.loads(data.decode("utf-8")).get("visibility")
            return VisibilityLevel(raw) if raw else None
        except Exception as e:
            logger.debug(f"No visibility for {record_id}: {e}")
            return None
