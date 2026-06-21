"""Service for managing AssetRecord objects."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..models.asset import AssetRecord, ComponentCondition, ComponentState
from ..models.repair import TriageAction, TriageItem, TriageReport
from ..storage.smart_discovery import SmartFileDiscovery
from ..utils.logging import get_logger
from .base import BaseService, ServiceConfig
from .storage_service import StorageService

logger = get_logger(__name__)

_PREFIX = "asset"


def _derive_action(cs: Optional[ComponentState], comp: Any) -> TriageAction:
    """Derive the recommended action from observed condition + manifest design flags."""
    if cs is None or cs.condition == ComponentCondition.UNKNOWN:
        return TriageAction.ASSESS
    if cs.condition == ComponentCondition.INTACT:
        return TriageAction.NO_ACTION
    if cs.condition == ComponentCondition.DAMAGED:
        if cs.repair_feasible is True:
            return TriageAction.REPAIR_IN_PLACE
        salvageable = getattr(comp, "salvageable", False) if comp else False
        replaceable = getattr(comp, "replaceable", False) if comp else False
        if salvageable:
            return TriageAction.HARVEST
        if replaceable:
            return TriageAction.SOURCE_NEW
        return TriageAction.DECOMMISSION
    if cs.condition == ComponentCondition.MISSING:
        replaceable = getattr(comp, "replaceable", False) if comp else False
        if replaceable:
            return TriageAction.SOURCE_NEW
        return TriageAction.DECOMMISSION
    return TriageAction.ASSESS


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
    # Triage report
    # ------------------------------------------------------------------

    async def generate_triage_report(self, asset_id: UUID) -> TriageReport:
        """Join AssetRecord + OKHManifest to produce a per-component TriageReport."""
        await self.ensure_initialized()

        record = await self.get(asset_id)
        if record is None:
            raise KeyError(f"AssetRecord {asset_id} not found")

        from .okh_service import OKHService

        okh_svc = await OKHService.get_instance()
        manifest = await okh_svc.get(UUID(record.manifest_id))

        # Build a lookup of observed states
        observed: Dict[str, ComponentState] = {
            cs.component_name: cs for cs in record.component_states
        }

        items: list[TriageItem] = []

        if manifest and manifest.components:
            for comp in manifest.components:
                cs = observed.get(comp.name)
                action = _derive_action(cs, comp)
                items.append(
                    TriageItem(
                        component_name=comp.name,
                        recommended_action=action,
                        condition=cs.condition.value if cs else "not_assessed",
                        repair_feasible=cs.repair_feasible if cs else None,
                        harvest_viable=cs.harvest_viable if cs else None,
                        source_required=cs.source_required if cs else None,
                        notes=cs.notes if cs else None,
                        replaceable=comp.replaceable,
                        salvageable=comp.salvageable,
                        consumable=comp.consumable,
                        part_number=comp.part_number,
                    )
                )
        else:
            # No manifest components — emit one item per observed state
            for cs in record.component_states:
                items.append(
                    TriageItem(
                        component_name=cs.component_name,
                        recommended_action=_derive_action(cs, None),
                        condition=cs.condition.value,
                        repair_feasible=cs.repair_feasible,
                        harvest_viable=cs.harvest_viable,
                        source_required=cs.source_required,
                        notes=cs.notes,
                    )
                )

        return TriageReport(
            asset_id=str(record.id),
            manifest_id=record.manifest_id,
            asset_tag=record.asset_tag,
            items=items,
            last_triaged_at=(
                record.last_triaged_at.isoformat() if record.last_triaged_at else None
            ),
            triage_notes=record.triage_notes,
        )

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
