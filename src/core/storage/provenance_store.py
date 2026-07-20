"""Record provenance store (federated-identity Slice 3).

Provenance is a **distinct plane** from the manifest content: who authored /
published a record, kept out of the design content hash so the same design
published by different people still deduplicates. Each record's provenance is one
JSON object under ``provenance/<record_id>.json`` in the object store, keyed by
the OKH manifest / OKW facility id. Not secret; federation propagation (riding the
signed catalog record) lands in a later slice.
"""

import json
import logging
from typing import Optional

from ..models.provenance import RecordProvenance
from ..services.storage_service import StorageService
from .constants import PROVENANCE_PREFIX, STORAGE_OBJECT_TYPE_PROVENANCE

logger = logging.getLogger(__name__)


class ProvenanceStore:
    """Object-store persistence for record provenance, keyed by record id."""

    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self._prefix = PROVENANCE_PREFIX

    def _key(self, record_id: str) -> str:
        return f"{self._prefix}/{record_id}.json"

    async def save(self, record_id: str, provenance: RecordProvenance) -> None:
        """Persist provenance for a record."""
        data = json.dumps(provenance.model_dump(mode="json")).encode("utf-8")
        await self.storage_service.manager.put_object(
            key=self._key(record_id),
            data=data,
            content_type="application/json",
            metadata={
                "type": STORAGE_OBJECT_TYPE_PROVENANCE,
                "record_id": record_id,
            },
        )

    async def load(self, record_id: str) -> Optional[RecordProvenance]:
        """Load provenance for a record, or None if absent/unreadable."""
        try:
            data = await self.storage_service.manager.get_object(self._key(record_id))
            return RecordProvenance(**json.loads(data.decode("utf-8")))
        except Exception as e:
            logger.debug(f"No provenance for {record_id}: {e}")
            return None
