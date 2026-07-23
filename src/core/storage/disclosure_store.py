"""Per-facility OKW disclosure profile store."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..models.disclosure import DisclosureProfile, default_disclosure_profile
from .constants import DISCLOSURE_PREFIX, STORAGE_OBJECT_TYPE_DISCLOSURE

if TYPE_CHECKING:
    from ..services.storage_service import StorageService

logger = logging.getLogger(__name__)


class DisclosureStore:
    """Object-store persistence for OKW disclosure profiles."""

    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self._prefix = DISCLOSURE_PREFIX

    def _key(self, facility_id: str) -> str:
        return f"{self._prefix}/{facility_id}.json"

    async def save(self, facility_id: str, profile: DisclosureProfile) -> None:
        await self.storage_service.manager.put_object(
            key=self._key(facility_id),
            data=profile.model_dump_json().encode("utf-8"),
            content_type="application/json",
            metadata={
                "type": STORAGE_OBJECT_TYPE_DISCLOSURE,
                "record_id": facility_id,
            },
        )

    async def load(self, facility_id: str) -> DisclosureProfile | None:
        try:
            data = await self.storage_service.manager.get_object(self._key(facility_id))
            return DisclosureProfile.model_validate_json(data.decode("utf-8"))
        except Exception as e:
            logger.debug(f"No disclosure for {facility_id}: {e}")
            return None

    async def load_or_default(self, facility_id: str) -> DisclosureProfile:
        return await self.load(facility_id) or default_disclosure_profile()
