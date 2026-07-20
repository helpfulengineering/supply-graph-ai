"""Capability grant store (federated-identity Slice 2).

Grants are signed but not secret, and are **not federated** (present-on-demand):
each is one JSON object under ``identity/grants/<grant_id>.json`` in the object
store (mirroring :class:`AuthStorage`). An in-memory index keyed by
``subject_did`` is built on first use — the auth hot path is
API key -> account -> subject DID -> grants -> effective permissions.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from ..models.capability import CapabilityGrant, Scope
from ..services.storage_service import StorageService
from .constants import IDENTITY_GRANTS_PREFIX, STORAGE_OBJECT_TYPE_CAPABILITY_GRANT

logger = logging.getLogger(__name__)


class GrantStore:
    """Object-store persistence + subject-keyed index for capability grants."""

    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self._prefix = IDENTITY_GRANTS_PREFIX
        self._index: Optional[Dict[str, List[CapabilityGrant]]] = None

    async def save_grant(self, grant: CapabilityGrant) -> None:
        """Persist a grant and update the in-memory index."""
        data = json.dumps(self._serialize(grant)).encode("utf-8")
        await self.storage_service.manager.put_object(
            key=self._key(grant.grant_id),
            data=data,
            content_type="application/json",
            metadata={
                "type": STORAGE_OBJECT_TYPE_CAPABILITY_GRANT,
                "grant_id": str(grant.grant_id),
                "subject_did": grant.subject_did,
            },
        )
        if self._index is not None:
            self._index.setdefault(grant.subject_did, []).append(grant)

    async def delete_grant(self, grant_id: UUID) -> None:
        """Revoke (delete) a grant and drop it from the index."""
        await self.storage_service.manager.delete_object(self._key(grant_id))
        if self._index is not None:
            for grants in self._index.values():
                grants[:] = [g for g in grants if g.grant_id != grant_id]

    async def list_for_subject(self, subject_did: str) -> List[CapabilityGrant]:
        """Return all grants whose subject is ``subject_did``."""
        await self._ensure_index()
        assert self._index is not None
        return list(self._index.get(subject_did, []))

    async def list_all(self) -> List[CapabilityGrant]:
        """Return every grant."""
        await self._ensure_index()
        assert self._index is not None
        return [g for grants in self._index.values() for g in grants]

    async def _ensure_index(self) -> None:
        if self._index is not None:
            return
        index: Dict[str, List[CapabilityGrant]] = {}
        prefix = f"{self._prefix}/"
        try:
            async for obj in self.storage_service.manager.list_objects(prefix=prefix):
                data = obj.get("data") or await self.storage_service.manager.get_object(
                    obj["key"]
                )
                try:
                    grant = self._deserialize(json.loads(data.decode("utf-8")))
                    index.setdefault(grant.subject_did, []).append(grant)
                except Exception as e:
                    logger.warning(
                        f"Failed to parse grant from {obj.get('key', 'unknown')}: {e}"
                    )
        except Exception as e:
            logger.error(f"Failed to build grant index: {e}")
            raise
        self._index = index

    def _key(self, grant_id: UUID) -> str:
        return f"{self._prefix}/{grant_id}.json"

    @staticmethod
    def _serialize(grant: CapabilityGrant) -> dict:
        payload = grant.signing_payload()
        payload["signature"] = grant.signature
        return payload

    @staticmethod
    def _deserialize(data: dict) -> CapabilityGrant:
        scope = data["scope"]
        return CapabilityGrant(
            grant_id=UUID(data["grant_id"]),
            issuer_did=data["issuer_did"],
            subject_did=data["subject_did"],
            permissions=data.get("permissions", []),
            coarse_floor=data.get("coarse_floor", []),
            scope=Scope(
                kind=scope["kind"], target=scope["target"], v=scope.get("v", 1)
            ),
            issued_at=datetime.fromisoformat(data["issued_at"]),
            not_before=(
                datetime.fromisoformat(data["not_before"])
                if data.get("not_before")
                else None
            ),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            delegated_from=(
                UUID(data["delegated_from"]) if data.get("delegated_from") else None
            ),
            signature=data.get("signature", ""),
        )
