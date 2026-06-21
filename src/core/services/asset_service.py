"""Service for managing AssetRecord objects."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..models.asset import AssetRecord, ComponentState
from ..storage.smart_discovery import SmartFileDiscovery
from ..utils.logging import get_logger
from .base import BaseService, ServiceConfig
from .storage_service import StorageService

logger = get_logger(__name__)

_PREFIX = "asset"


class AssetService(BaseService["AssetService"]):
    """CRUD service for AssetRecord — physical state of device units in the field."""

    def __init__(
        self, service_name: str = "AssetService", config: Optional[ServiceConfig] = None
    ) -> None:
        super().__init__(service_name, config)
        self.storage: Optional[StorageService] = None

    async def _initialize_dependencies(self) -> None:
        self.storage = await StorageService.get_instance()
        if not self.storage._configured:
            from ...config.storage_config import get_default_storage_config

            config = get_default_storage_config()
            await self.storage.configure(config)
        self.logger.info("AssetService dependencies initialized")

    async def initialize(self) -> None:
        await self.ensure_initialized()
        await self._ensure_domains_registered()
        self.add_dependency("storage", self.storage)
        self.logger.info("AssetService initialized")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, asset_data: Dict[str, Any]) -> AssetRecord:
        """Persist a new AssetRecord at ``asset/{id}.json``."""
        async with self.track_request("create_asset"):
            await self.ensure_initialized()
            record = (
                asset_data
                if isinstance(asset_data, AssetRecord)
                else AssetRecord.from_dict(asset_data)
            )
            if self.storage and self.storage.manager:
                key = f"{_PREFIX}/{record.id}.json"
                await self.storage.manager.put_object(
                    key, json.dumps(record.to_dict(), indent=2, default=str).encode()
                )
                self.logger.info(f"Created AssetRecord at {key}")
            return record

    async def get(self, asset_id: UUID) -> Optional[AssetRecord]:
        """Return the AssetRecord with the given ID, or None."""
        async with self.track_request("get_asset"):
            await self.ensure_initialized()
            if not (self.storage and self.storage.manager):
                return None
            discovery = SmartFileDiscovery(self.storage.manager)
            for fi in await discovery.discover_files(_PREFIX):
                try:
                    data = json.loads(
                        (await self.storage.manager.get_object(fi.key)).decode()
                    )
                    if data.get("id") == str(asset_id):
                        return AssetRecord.from_dict(data)
                except Exception as exc:
                    logger.debug(f"Skipping {fi.key}: {exc}")
            return None

    async def list(self, manifest_id: Optional[str] = None) -> List[AssetRecord]:
        """Return all AssetRecords, optionally filtered by manifest_id."""
        await self.ensure_initialized()
        if not (self.storage and self.storage.manager):
            return []
        discovery = SmartFileDiscovery(self.storage.manager)
        records: Dict[str, AssetRecord] = {}
        for fi in await discovery.discover_files(_PREFIX):
            try:
                data = json.loads(
                    (await self.storage.manager.get_object(fi.key)).decode()
                )
                record = AssetRecord.from_dict(data)
                if manifest_id and record.manifest_id != manifest_id:
                    continue
                # Deduplicate: keep the record we already have (first seen wins)
                key = str(record.id)
                if key not in records:
                    records[key] = record
            except Exception as exc:
                logger.debug(f"Skipping {fi.key}: {exc}")
        return list(records.values())

    async def update(self, asset_id: UUID, asset_data: Dict[str, Any]) -> AssetRecord:
        """Replace an AssetRecord in-place at its existing storage key."""
        await self.ensure_initialized()
        record = (
            asset_data
            if isinstance(asset_data, AssetRecord)
            else AssetRecord.from_dict(asset_data)
        )
        if self.storage and self.storage.manager:
            key = await self._find_key(asset_id) or f"{_PREFIX}/{asset_id}.json"
            await self.storage.manager.put_object(
                key, json.dumps(record.to_dict(), indent=2, default=str).encode()
            )
            self.logger.info(f"Updated AssetRecord at {key}")
        return record

    async def delete(self, asset_id: UUID) -> bool:
        """Delete an AssetRecord by ID. Returns True if deleted."""
        await self.ensure_initialized()
        if not (self.storage and self.storage.manager):
            return False
        key = await self._find_key(asset_id)
        if key is None:
            return False
        result = await self.storage.manager.delete_object(key)
        self.logger.info(f"Deleted AssetRecord at {key}")
        return result

    # ------------------------------------------------------------------
    # Triage
    # ------------------------------------------------------------------

    async def record_triage(
        self,
        asset_id: UUID,
        states: List[ComponentState],
        triage_notes: Optional[str] = None,
    ) -> AssetRecord:
        """Upsert component states by component_name and stamp last_triaged_at."""
        await self.ensure_initialized()
        record = await self.get(asset_id)
        if record is None:
            raise KeyError(f"AssetRecord {asset_id} not found")

        existing: Dict[str, ComponentState] = {
            cs.component_name: cs for cs in record.component_states
        }
        for state in states:
            existing[state.component_name] = state

        record.component_states = list(existing.values())
        record.last_triaged_at = datetime.now(tz=timezone.utc)
        if triage_notes is not None:
            record.triage_notes = triage_notes

        return await self.update(asset_id, record.to_dict())

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _find_key(self, asset_id: UUID) -> Optional[str]:
        if not (self.storage and self.storage.manager):
            return None
        discovery = SmartFileDiscovery(self.storage.manager)
        for fi in await discovery.discover_files(_PREFIX):
            try:
                data = json.loads(
                    (await self.storage.manager.get_object(fi.key)).decode()
                )
                if data.get("id") == str(asset_id):
                    return fi.key
            except Exception:
                continue
        return None
