"""Identity binding + trust-on-follow directory stores (Slice 7)."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from ..models.binding import DirectoryEntry, IdentityBinding
from .constants import (
    BINDINGS_PREFIX,
    DIRECTORY_PREFIX,
    STORAGE_OBJECT_TYPE_BINDING,
    STORAGE_OBJECT_TYPE_DIRECTORY,
)

if TYPE_CHECKING:
    from ..services.storage_service import StorageService

logger = logging.getLogger(__name__)


class BindingStore:
    """Object-store persistence for identity bindings."""

    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self._prefix = BINDINGS_PREFIX
        self._index: Optional[Dict[str, IdentityBinding]] = None

    def _key(self, binding_id: UUID) -> str:
        return f"{self._prefix}/{binding_id}.json"

    async def save(self, binding: IdentityBinding) -> None:
        data = json.dumps(binding.model_dump(mode="json")).encode("utf-8")
        await self.storage_service.manager.put_object(
            key=self._key(binding.binding_id),
            data=data,
            content_type="application/json",
            metadata={
                "type": STORAGE_OBJECT_TYPE_BINDING,
                "binding_id": str(binding.binding_id),
                "subject_did": binding.subject_did,
                "kind": binding.kind,
            },
        )
        if self._index is not None:
            self._index[str(binding.binding_id)] = binding

    async def load(self, binding_id: UUID) -> Optional[IdentityBinding]:
        await self._ensure_index()
        assert self._index is not None
        return self._index.get(str(binding_id))

    async def list_for_subject(self, subject_did: str) -> List[IdentityBinding]:
        await self._ensure_index()
        assert self._index is not None
        return [b for b in self._index.values() if b.subject_did == subject_did]

    async def find_by_external_id(self, external_id: str) -> Optional[IdentityBinding]:
        await self._ensure_index()
        assert self._index is not None
        for b in self._index.values():
            if b.external_id == external_id:
                return b
        return None

    async def list_all(self) -> List[IdentityBinding]:
        await self._ensure_index()
        assert self._index is not None
        return list(self._index.values())

    async def _ensure_index(self) -> None:
        if self._index is not None:
            return
        index: Dict[str, IdentityBinding] = {}
        prefix = f"{self._prefix}/"
        try:
            async for obj in self.storage_service.manager.list_objects(prefix=prefix):
                data = (
                    obj["data"]
                    if "data" in obj
                    else await self.storage_service.manager.get_object(obj["key"])
                )
                try:
                    binding = IdentityBinding(**json.loads(data.decode("utf-8")))
                    index[str(binding.binding_id)] = binding
                except Exception as e:
                    logger.warning(
                        f"Failed to parse binding from {obj.get('key')}: {e}"
                    )
        except Exception as e:
            logger.error(f"Failed to build binding index: {e}")
            raise
        self._index = index


class DirectoryStore:
    """Local trust-on-follow directory (peacetime registry posture)."""

    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self._prefix = DIRECTORY_PREFIX
        self._index: Optional[Dict[str, DirectoryEntry]] = None

    def _key(self, did: str) -> str:
        safe = did.replace("/", "_")
        return f"{self._prefix}/{safe}.json"

    async def save(self, entry: DirectoryEntry) -> None:
        data = json.dumps(entry.model_dump(mode="json")).encode("utf-8")
        await self.storage_service.manager.put_object(
            key=self._key(entry.did),
            data=data,
            content_type="application/json",
            metadata={
                "type": STORAGE_OBJECT_TYPE_DIRECTORY,
                "did": entry.did,
            },
        )
        if self._index is not None:
            self._index[entry.did] = entry

    async def load(self, did: str) -> Optional[DirectoryEntry]:
        await self._ensure_index()
        assert self._index is not None
        return self._index.get(did)

    async def list_all(self) -> List[DirectoryEntry]:
        await self._ensure_index()
        assert self._index is not None
        return list(self._index.values())

    async def _ensure_index(self) -> None:
        if self._index is not None:
            return
        index: Dict[str, DirectoryEntry] = {}
        prefix = f"{self._prefix}/"
        try:
            async for obj in self.storage_service.manager.list_objects(prefix=prefix):
                data = (
                    obj["data"]
                    if "data" in obj
                    else await self.storage_service.manager.get_object(obj["key"])
                )
                try:
                    entry = DirectoryEntry(**json.loads(data.decode("utf-8")))
                    index[entry.did] = entry
                except Exception as e:
                    logger.warning(
                        f"Failed to parse directory entry from {obj.get('key')}: {e}"
                    )
        except Exception as e:
            logger.error(f"Failed to build directory index: {e}")
            raise
        self._index = index
