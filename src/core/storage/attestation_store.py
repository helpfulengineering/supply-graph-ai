"""Attestation store (federated-identity Slice 6).

Durable signed facts about subjects / content hashes. Not secret; keyed by
attestation_id with secondary indexes for subject_did and content_hash.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from ..models.attestation import Attestation
from .constants import ATTESTATIONS_PREFIX, STORAGE_OBJECT_TYPE_ATTESTATION

if TYPE_CHECKING:
    from ..services.storage_service import StorageService

logger = logging.getLogger(__name__)


class AttestationStore:
    """Object-store persistence for attestations."""

    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self._prefix = ATTESTATIONS_PREFIX
        self._index: Optional[Dict[str, Attestation]] = None

    def _key(self, attestation_id: UUID) -> str:
        return f"{self._prefix}/{attestation_id}.json"

    async def save(self, attestation: Attestation) -> None:
        """Persist an attestation (overwrites same id)."""
        data = json.dumps(attestation.model_dump(mode="json")).encode("utf-8")
        await self.storage_service.manager.put_object(
            key=self._key(attestation.attestation_id),
            data=data,
            content_type="application/json",
            metadata={
                "type": STORAGE_OBJECT_TYPE_ATTESTATION,
                "attestation_id": str(attestation.attestation_id),
                "subject_did": attestation.subject_did,
                "attestation_type": attestation.type,
            },
        )
        if self._index is not None:
            self._index[str(attestation.attestation_id)] = attestation

    async def load(self, attestation_id: UUID) -> Optional[Attestation]:
        """Load one attestation by id, or None."""
        await self._ensure_index()
        assert self._index is not None
        return self._index.get(str(attestation_id))

    async def list_for_subject(self, subject_did: str) -> List[Attestation]:
        """All attestations whose subject is ``subject_did``."""
        await self._ensure_index()
        assert self._index is not None
        return [a for a in self._index.values() if a.subject_did == subject_did]

    async def list_for_content(self, content_hash: str) -> List[Attestation]:
        """Attestations bound directly to ``content_hash``."""
        await self._ensure_index()
        assert self._index is not None
        return [a for a in self._index.values() if a.content_hash == content_hash]

    async def list_for_catalog(self, manifest_content_hash: str) -> List[Attestation]:
        """Attestations that should ride a catalog record for this design hash.

        Includes direct ``content_hash`` matches and ``certified`` attestations
        whose claim carries ``manifest_content_hash`` (bundle hash lives in
        ``content_hash`` / claim.bundle_hash).
        """
        await self._ensure_index()
        assert self._index is not None
        out: List[Attestation] = []
        for a in self._index.values():
            if a.content_hash == manifest_content_hash:
                out.append(a)
                continue
            if a.claim.get("manifest_content_hash") == manifest_content_hash:
                out.append(a)
        return out

    async def list_all(self) -> List[Attestation]:
        """Every attestation held by this node."""
        await self._ensure_index()
        assert self._index is not None
        return list(self._index.values())

    async def _ensure_index(self) -> None:
        if self._index is not None:
            return
        index: Dict[str, Attestation] = {}
        prefix = f"{self._prefix}/"
        try:
            async for obj in self.storage_service.manager.list_objects(prefix=prefix):
                if "data" in obj:
                    data = obj["data"]
                else:
                    data = await self.storage_service.manager.get_object(obj["key"])
                try:
                    att = Attestation(**json.loads(data.decode("utf-8")))
                    index[str(att.attestation_id)] = att
                except Exception as e:
                    logger.warning(
                        f"Failed to parse attestation from {obj.get('key')}: {e}"
                    )
        except Exception as e:
            logger.error(f"Failed to build attestation index: {e}")
            raise
        self._index = index
