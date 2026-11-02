"""Generation-provenance store (#566).

How a manifest was generated, keyed by record id and kept out of the design
content hash. Same plane pattern as :class:`VisibilityStore`.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Optional

from .constants import (
    GENERATION_PROVENANCE_PREFIX,
    STORAGE_OBJECT_TYPE_GENERATION_PROVENANCE,
)

if TYPE_CHECKING:
    from ..services.storage_service import StorageService

logger = logging.getLogger(__name__)


class GenerationProvenanceStore:
    """Object-store persistence for a generation sidecar, keyed by record id."""

    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self._prefix = GENERATION_PROVENANCE_PREFIX

    def _key(self, record_id: str) -> str:
        return f"{self._prefix}/{record_id}.json"

    async def save(self, record_id: str, record: dict[str, Any]) -> None:
        """Persist the sidecar for a record."""
        data = json.dumps(record).encode("utf-8")
        await self.storage_service.manager.put_object(
            key=self._key(record_id),
            data=data,
            content_type="application/json",
            metadata={
                "type": STORAGE_OBJECT_TYPE_GENERATION_PROVENANCE,
                "record_id": record_id,
            },
        )

    async def load(self, record_id: str) -> Optional[dict[str, Any]]:
        """Load the sidecar for a record, or None if absent or unreadable."""
        try:
            data = await self.storage_service.manager.get_object(self._key(record_id))
            loaded = json.loads(data.decode("utf-8"))
            return loaded if isinstance(loaded, dict) else None
        except Exception as e:
            logger.debug(f"No generation provenance for {record_id}: {e}")
            return None
