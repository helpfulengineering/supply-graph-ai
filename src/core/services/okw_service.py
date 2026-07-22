import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from ..domains.cooking.models import KitchenCapability
from ..models.okw import FacilityStatus, Location, ManufacturingFacility
from ..models.provenance import RecordProvenance, apply_ohm_metadata
from ..models.disclosure import (
    DisclosureAudience,
    DisclosureProfile,
    default_disclosure_profile,
    groups_for_audience,
    project_facility,
)
from ..models.visibility import (
    DEFAULT_VISIBILITY,
    LEGACY_VISIBILITY,
    VisibilityLevel,
)
from ..storage.disclosure_store import DisclosureStore
from ..storage.provenance_store import ProvenanceStore
from ..storage.visibility_store import VisibilityStore
from ..storage.smart_discovery import SmartFileDiscovery
from ..taxonomy import taxonomy
from ..utils.logging import get_logger
from ..validation.error_codes import VALIDATION_ERROR_CODE, VALIDATION_WARNING_CODE
from ..validation.uuid_validator import UUIDValidator
from .base import BaseService, ServiceConfig
from .storage_service import StorageService

logger = get_logger(__name__)


# --- Unified network-space projection + filtering (for GET /api/okw/spaces) ----

# Status vocabularies differ by source (local: Active/Planned/…; MoM:
# confirmed/seeded). Normalize to a small shared set for a coherent filter.
_STATUS_NORMALIZED = {
    "active": "active",
    "confirmed": "active",
    "planned": "tentative",
    "seeded": "tentative",
    "temporary closure": "tentative",
    "closed": "inactive",
    "inactive": "inactive",
}


def _normalize_status(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    key = value.strip().lower()
    return _STATUS_NORMALIZED.get(key, key or None)


def _canonical_processes(raw: List[str]) -> List[str]:
    processes: List[str] = []
    for p in raw or []:
        cid = taxonomy.normalize(p)
        if cid and cid not in processes:
            processes.append(cid)
    return processes


def _local_facility_to_space(
    f: ManufacturingFacility, *, require_coords: bool = True
) -> Optional[Dict[str, Any]]:
    """Project a local facility to the unified network-space shape.

    Returns ``None`` when the facility has no plottable coordinates *and*
    ``require_coords`` is True (the browse/map surface needs a point). For
    matching, callers pass ``require_coords=False`` so a capability-valid
    facility is not dropped from the candidate pool for lacking geography;
    ``lat``/``lon`` are then ``None``.
    """
    coords = f.location.coordinates() if f.location else None
    if coords is None and require_coords:
        return None
    loc = f.location
    addr = getattr(loc, "address", None)
    owner = getattr(f, "owner", None)
    return {
        "id": str(f.id),
        "name": f.name,
        "lat": coords.latitude if coords else None,
        "lon": coords.longitude if coords else None,
        "city": getattr(addr, "city", None) or getattr(loc, "city", None),
        "region": getattr(addr, "region", None) or getattr(loc, "region", None),
        "country": getattr(addr, "country", None) or getattr(loc, "country", None),
        "source": "local",
        "status": _normalize_status(
            f.facility_status.value if getattr(f, "facility_status", None) else None
        ),
        "processes": _canonical_processes(f.manufacturing_processes),
        "access_type": f.access_type.value if getattr(f, "access_type", None) else None,
        "url": getattr(owner, "website", None),
    }


def _mom_stub_facility(s: Dict[str, Any]) -> ManufacturingFacility:
    """Build a matchable ManufacturingFacility stub from a cached MoM space.

    MoM spaces have no equipment detail, so matching against them is process-level
    (their canonical processes vs the design's requirements) — i.e. "spaces that
    claim these processes, worth contacting".
    """
    return ManufacturingFacility(
        name=s["name"],
        location=Location(gps_coordinates=f"{s['lat']}, {s['lon']}"),
        facility_status=FacilityStatus.ACTIVE,
        manufacturing_processes=s.get("processes", []),
    )


def _mom_space_to_space(s: Dict[str, Any]) -> Dict[str, Any]:
    """Project a (cached, already-enriched) MoM space to the unified shape."""
    return {
        "id": s["space"],
        "name": s["name"],
        "lat": s["lat"],
        "lon": s["lon"],
        "city": s.get("city"),
        "region": None,  # MoM has no sub-national region
        "country": s.get("country"),
        "source": "mom",
        "status": _normalize_status(s.get("status")),
        "processes": s.get("processes", []),
        "access_type": None,  # MoM does not express access type
        "url": s.get("url"),
    }


def _ci(value: Optional[str]) -> Optional[str]:
    return value.strip().lower() if isinstance(value, str) else value


def filter_network_spaces(
    spaces: List[Dict[str, Any]],
    *,
    country: Optional[str] = None,
    city: Optional[str] = None,
    process: Optional[str] = None,
    source: Optional[str] = None,
    status: Optional[str] = None,
    region: Optional[str] = None,
    access_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Apply the network filters (pure).

    Cross-source axes (country/city/process/source/status) hard-exclude
    non-matches. Local-only axes (region/access_type) that a space *cannot*
    express don't exclude it — the space is kept, flagged ``ambiguous``, and
    sorted after the definite matches. A space that *can* express a local-only
    axis but doesn't match is excluded.
    """
    kept: List[Dict[str, Any]] = []
    for sp in spaces:
        if source and sp.get("source") != source:
            continue
        if country and _ci(sp.get("country")) != _ci(country):
            continue
        if city and (not sp.get("city") or _ci(city) not in _ci(sp["city"])):
            continue
        if status and sp.get("status") != _ci(status):
            continue
        if process and process not in (sp.get("processes") or []):
            continue

        ambiguous = False
        excluded = False
        for axis, want in (("region", region), ("access_type", access_type)):
            if not want:
                continue
            have = sp.get(axis)
            if have is None:
                ambiguous = True  # source can't express this axis
            elif _ci(have) != _ci(want):
                excluded = True
                break
        if excluded:
            continue
        kept.append({**sp, "ambiguous": ambiguous})

    # Definite matches first, ambiguous last (stable within each group).
    kept.sort(key=lambda s: s.get("ambiguous", False))
    return kept


# --- Local OKW JSON dir (dev convenience; storage-only, never unioned) ---------


def resolve_matching_local_okw_json_dir() -> Optional[str]:
    """Resolve the optional local OKW directory from env or imported settings.

    Expands ``~`` and resolves relative paths against the process working
    directory. Logs a warning when set but not pointing at a directory so
    misconfiguration is visible. Returns ``None`` when unset/invalid.
    """
    from src.config import settings as _settings

    val = getattr(_settings, "MATCHING_LOCAL_OKW_JSON_DIR", None)
    raw = str(val).strip() if val else ""
    if not raw:
        raw = (os.getenv("MATCHING_LOCAL_OKW_JSON_DIR") or "").strip()
    if not raw:
        return None

    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        resolved = path.resolve()
    except OSError as e:
        logger.warning(
            "MATCHING_LOCAL_OKW_JSON_DIR could not be resolved; using remote OKW listing",
            extra={"raw": raw, "error": str(e)},
        )
        return None

    if not resolved.is_dir():
        logger.warning(
            "MATCHING_LOCAL_OKW_JSON_DIR is not a directory; using remote OKW listing",
            extra={"path": str(resolved), "raw": raw},
        )
        return None
    logger.info(
        "MATCHING_LOCAL_OKW_JSON_DIR resolved successfully",
        extra={"directory": str(resolved), "raw_input": raw},
    )
    return str(resolved)


def load_facilities_from_local_okw_json_dir(
    directory: str,
    domain: str,
    request_id: str = "",
) -> List[Any]:
    """Load OKW-shaped JSON files from disk (local/dev when remote listing hangs)."""
    root = Path(directory)
    if not root.is_dir():
        return []

    facilities_by_id: Dict[UUID, Any] = {}
    for path in sorted(root.rglob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(
                "Skipping unreadable OKW JSON file",
                extra={"request_id": request_id, "path": str(path), "error": str(e)},
            )
            continue
        try:
            if domain == "manufacturing":
                if KitchenCapability.is_cooking_capability(raw):
                    continue
                fixed = UUIDValidator.validate_and_fix_okw_data(raw)
                facility = ManufacturingFacility.from_dict(fixed)
                facilities_by_id[facility.id] = facility
            elif domain == "cooking":
                if not KitchenCapability.is_cooking_capability(raw):
                    continue
                facility = KitchenCapability.from_dict(raw)
                facilities_by_id[facility.id] = facility
            else:
                return []
        except Exception as e:
            logger.warning(
                "Skipping invalid OKW JSON file for local dir load",
                extra={"request_id": request_id, "path": str(path), "error": str(e)},
            )
    return list(facilities_by_id.values())


class OKWService(BaseService["OKWService"]):
    """
    Service for managing OKW manufacturing facilities.

    This service provides functionality for:
    - Creating, reading, updating, and deleting OKW facilities
    - Validating OKW facility data
    - Managing OKW facility storage and retrieval
    - Integration with validation systems
    """

    def __init__(
        self, service_name: str = "OKWService", config: Optional[ServiceConfig] = None
    ) -> None:
        """Initialize the OKW service with base service functionality."""
        super().__init__(service_name, config)
        self.storage: Optional[StorageService] = None

    async def _initialize_dependencies(self) -> None:
        """Initialize storage dependency and ensure it is configured.

        This is invoked by :class:`BaseService` during first-time initialization.
        """
        # Initialize storage service
        self.storage = await StorageService.get_instance()

        # Configure storage service if not already configured
        if not self.storage._configured:
            from ...config.storage_config import get_default_storage_config

            config = get_default_storage_config()
            await self.storage.configure(config)

        self.logger.info("OKW service dependencies initialized")

    async def initialize(self) -> None:
        """Ensure domains are registered, attach storage, and complete base-service setup."""
        await self.ensure_initialized()

        # Ensure domains are registered (for fallback mode when server startup doesn't run)
        await self._ensure_domains_registered()

        # Add dependencies to base service
        self.add_dependency("storage", self.storage)

        self.logger.info("OKW service initialized successfully")

    async def create(
        self,
        facility_data: Dict[str, Any],
        created_by: Optional[str] = None,
        provenance: Optional[RecordProvenance] = None,
    ) -> ManufacturingFacility:
        """Persist a facility JSON at ``okw/{facility_id}.json`` when storage is configured.

        Args:
            facility_data: Raw dict or an existing ``ManufacturingFacility`` instance.
            created_by: Optional account id to attribute the record to; persisted
                alongside the facility JSON (see federated-identity Slice 1).
            provenance: Optional record-level authorship/publication provenance
                (federated-identity Slice 3).

        New records stamp ``private`` visibility (Slice 4); promote with
        :meth:`set_visibility` to share via the federation catalog.

        Returns:
            The created ``ManufacturingFacility``.
        """
        async with self.track_request("create_okw_facility"):
            await self.ensure_initialized()
            self.logger.info("Creating new manufacturing facility")

            # Create facility object - handle both dict and ManufacturingFacility inputs
            if isinstance(facility_data, ManufacturingFacility):
                facility = facility_data
            else:
                facility = ManufacturingFacility.from_dict(facility_data)

            # Store directly under okw/ using the facility UUID as the filename.
            # No subdirectory is enforced; users may organise beneath okw/ freely.
            # SmartFileDiscovery uses directory-prefix listing as its primary
            # strategy, so no special suffix is required for discoverability.
            if self.storage and self.storage.manager:
                filename = f"okw/{str(facility.id)}.json"

                # OHM-namespaced metadata (account attribution) is carried through
                # explicitly because to_dict() is a whitelist that drops ohm_* keys —
                # this is what lets ohm_created_by survive a federation ingest.
                payload = apply_ohm_metadata(
                    facility.to_dict(), facility_data, created_by
                )
                facility_json = json.dumps(
                    payload, indent=2, ensure_ascii=False, default=str
                )
                await self.storage.manager.put_object(
                    filename, facility_json.encode("utf-8")
                )
                self.logger.info(f"Saved OKW facility to {filename}")

                # Provenance + visibility live in their own planes (out of the
                # content hash). Visibility defaults to private — opt-in to share.
                if provenance is not None:
                    await self._provenance_store().save(str(facility.id), provenance)
                await self._visibility_store().save(
                    str(facility.id), DEFAULT_VISIBILITY
                )

            return facility

    def _provenance_store(self) -> ProvenanceStore:
        """Lazily build the provenance store over the configured storage."""
        return ProvenanceStore(self.storage)

    def _visibility_store(self) -> VisibilityStore:
        """Lazily build the visibility store over the configured storage."""
        return VisibilityStore(self.storage)

    def _disclosure_store(self) -> DisclosureStore:
        return DisclosureStore(self.storage)

    async def get_provenance(self, facility_id: UUID) -> Optional[RecordProvenance]:
        """Return the stored provenance for a facility, or None."""
        await self.ensure_initialized()
        if not self.storage or not self.storage.manager:
            return None
        return await self._provenance_store().load(str(facility_id))

    async def get_visibility(self, facility_id: UUID) -> VisibilityLevel:
        """Return visibility for a facility.

        Missing (pre-Slice-4) records resolve to ``followers`` so they keep
        their prior shareable posture; new creates stamp ``private`` explicitly.
        """
        await self.ensure_initialized()
        if not self.storage or not self.storage.manager:
            return LEGACY_VISIBILITY
        loaded = await self._visibility_store().load(str(facility_id))
        return loaded if loaded is not None else LEGACY_VISIBILITY

    async def set_visibility(
        self, facility_id: UUID, level: VisibilityLevel
    ) -> VisibilityLevel:
        """Set share policy for a facility. Record must already exist."""
        await self.ensure_initialized()
        if not self.storage or not self.storage.manager:
            raise RuntimeError("Storage service not available")
        if await self.get(facility_id) is None:
            raise LookupError(f"OKW facility {facility_id} not found")
        await self._visibility_store().save(str(facility_id), level)
        return level

    async def get_disclosure(self, facility_id: UUID) -> DisclosureProfile:
        """Return disclosure profile (fail-closed defaults if unset)."""
        await self.ensure_initialized()
        if not self.storage or not self.storage.manager:
            return default_disclosure_profile()
        return await self._disclosure_store().load_or_default(str(facility_id))

    async def set_disclosure(
        self, facility_id: UUID, profile: DisclosureProfile
    ) -> DisclosureProfile:
        await self.ensure_initialized()
        if not self.storage or not self.storage.manager:
            raise RuntimeError("Storage service not available")
        if await self.get(facility_id) is None:
            raise LookupError(f"OKW facility {facility_id} not found")
        await self._disclosure_store().save(str(facility_id), profile)
        return profile

    async def project_for_visibility(self, facility: ManufacturingFacility) -> dict:
        """Redacted facility dict for the facility's current visibility level."""
        visibility = await self.get_visibility(facility.id)
        if visibility == VisibilityLevel.PRIVATE:
            return {}
        audience = (
            DisclosureAudience.PUBLIC
            if visibility == VisibilityLevel.PUBLIC
            else DisclosureAudience.FOLLOWERS
        )
        profile = await self.get_disclosure(facility.id)
        groups = groups_for_audience(profile, audience)
        return project_facility(facility.to_dict(), groups=groups)

    async def get(self, facility_id: UUID) -> Optional[ManufacturingFacility]:
        """Discover ``okw/`` files and return the most recently modified row matching ``facility_id``.

        Args:
            facility_id: Target facility UUID.

        Returns:
            ``ManufacturingFacility`` when found; ``None`` if storage is missing or no match.
        """
        async with self.track_request("get_okw_facility"):
            await self.ensure_initialized()
            self.logger.info(f"Getting manufacturing facility with ID {facility_id}")

            if self.storage:
                # Use smart discovery to find OKW files
                discovery = SmartFileDiscovery(self.storage.manager)
                file_infos = await discovery.discover_files("okw")

                self.logger.info(
                    f"Found {len(file_infos)} OKW files using smart discovery"
                )

                # Search through OKW files for the matching ID
                # If multiple files have the same ID, prefer the most recently modified one
                matching_facilities = []
                for file_info in file_infos:
                    try:
                        data = await self.storage.manager.get_object(file_info.key)
                        content = data.decode("utf-8")
                        okw_data = json.loads(content)

                        # Validate and fix UUID issues
                        fixed_okw_data = UUIDValidator.validate_and_fix_okw_data(
                            okw_data
                        )

                        facility = ManufacturingFacility.from_dict(fixed_okw_data)
                        if facility.id == facility_id:
                            # Store with file info for sorting
                            matching_facilities.append((file_info, facility))
                    except Exception as e:
                        self.logger.error(
                            f"Failed to load OKW file {file_info.key}: {e}"
                        )
                        continue

                # If multiple matches, return the most recently modified one
                if matching_facilities:
                    # Sort by last_modified (most recent first)
                    matching_facilities.sort(
                        key=lambda x: (
                            x[0].last_modified if hasattr(x[0], "last_modified") else ""
                        ),
                        reverse=True,
                    )
                    self.logger.info(
                        f"Found {len(matching_facilities)} file(s) with ID {facility_id}, using most recent: {matching_facilities[0][0].key}"
                    )
                    return matching_facilities[0][1]

            return None

    async def get_by_id(self, facility_id: UUID) -> Optional[ManufacturingFacility]:
        """Compatibility alias for :meth:`get`.

        Args:
            facility_id: Target facility UUID.

        Returns:
            Matching ``ManufacturingFacility`` or ``None`` when not found.
        """
        return await self.get(facility_id)

    async def list(
        self,
        page: int = 1,
        page_size: int = 100,
        filter_params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[ManufacturingFacility], int]:
        """List manufacturing facilities found under the ``okw/`` prefix.

        Returns only ``ManufacturingFacility`` objects.  Any file under
        ``okw/`` that is identified as cooking capability (by
        ``KitchenCapability.is_cooking_capability()``) is skipped and logged at
        DEBUG level so the two capability types remain strictly separated.

        Returns:
            A tuple of ``(facilities, total_count)`` where every element
            in ``facilities`` is a ``ManufacturingFacility`` instance.

        Args:
            page: 1-based page index.
            page_size: Page length.
            filter_params: Reserved for future server-side filtering.
        """
        await self.ensure_initialized()
        logger.info(
            f"Listing manufacturing facilities (page={page}, page_size={page_size})"
        )

        if not self.storage:
            return [], 0
        if not self.storage.manager:
            logger.warning(
                "Storage manager is None (storage configure may have failed). "
                "Check logs for 'Failed to configure storage'. Returning 0 facilities."
            )
            return [], 0

        # Use smart discovery to find OKW files
        discovery = SmartFileDiscovery(self.storage.manager)
        file_infos = await discovery.discover_files("okw")

        logger.info(f"Found {len(file_infos)} OKW files using smart discovery")

        # Process files and deduplicate by facility ID
        facilities_by_id: Dict[UUID, ManufacturingFacility] = {}
        file_info_by_id: Dict[UUID, Any] = {}

        for file_info in file_infos:
            try:
                data = await self.storage.manager.get_object(file_info.key)
                content = data.decode("utf-8")
                okw_data = json.loads(content)

                # Skip files that are cooking capabilities — they belong to list_kitchens()
                if KitchenCapability.is_cooking_capability(okw_data):
                    logger.debug(f"Skipping kitchen file {file_info.key} in list()")
                    continue

                # Validate and fix UUID issues
                fixed_okw_data = UUIDValidator.validate_and_fix_okw_data(okw_data)

                facility = ManufacturingFacility.from_dict(fixed_okw_data)
                facility_id = facility.id

                # If we haven't seen this ID, or this file is more recent, keep it
                if facility_id not in facilities_by_id:
                    facilities_by_id[facility_id] = facility
                    file_info_by_id[facility_id] = file_info
                else:
                    # Compare last_modified dates to keep the most recent
                    existing_modified = (
                        file_info_by_id[facility_id].last_modified
                        if hasattr(file_info_by_id[facility_id], "last_modified")
                        else None
                    )
                    current_modified = (
                        file_info.last_modified
                        if hasattr(file_info, "last_modified")
                        else None
                    )

                    if current_modified and (
                        not existing_modified or current_modified > existing_modified
                    ):
                        facilities_by_id[facility_id] = facility
                        file_info_by_id[facility_id] = file_info
                        logger.debug(
                            f"Replacing facility {facility_id} with more recent version from {file_info.key}"
                        )
            except Exception as e:
                logger.error(f"Failed to load OKW file {file_info.key}: {e}")
                continue

        # Convert dict values to list and apply pagination
        unique_facilities = list(facilities_by_id.values())
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_facilities = unique_facilities[start_idx:end_idx]

        logger.info(
            f"Found {len(file_infos)} OKW files, {len(unique_facilities)} unique facilities (page {page}: {len(paginated_facilities)} facilities)"
        )

        return paginated_facilities, len(unique_facilities)

    async def list_facilities(
        self,
        limit: int = 100,
        offset: int = 0,
        facility_type: Optional[str] = None,
        status: Optional[str] = None,
        location: Optional[str] = None,
    ) -> List[ManufacturingFacility]:
        """CLI-oriented wrapper around :meth:`list` using ``limit``/``offset``.

        Args:
            limit: Maximum facilities to return.
            offset: Number of facilities to skip before returning results.
            facility_type: Optional future filter key (currently forwarded only).
            status: Optional future filter key (currently forwarded only).
            location: Optional future filter key (currently forwarded only).

        Returns:
            List of ``ManufacturingFacility`` objects for the requested page.
        """
        # Convert limit/offset to page/page_size
        page_size = limit
        page = (offset // page_size) + 1

        # Build filter parameters
        filter_params = {}
        if facility_type:
            filter_params["facility_type"] = facility_type
        if status:
            filter_params["status"] = status
        if location:
            filter_params["location"] = location

        facilities, total = await self.list(
            page=page, page_size=page_size, filter_params=filter_params
        )
        return facilities

    async def get_network_spaces(
        self,
        *,
        include_mom: bool = True,
        force_refresh: bool = False,
        country: Optional[str] = None,
        city: Optional[str] = None,
        process: Optional[str] = None,
        source: Optional[str] = None,
        status: Optional[str] = None,
        region: Optional[str] = None,
        access_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build the unified, server-filtered network surface: local OKW ∪ MoM.

        Each space is source-labeled and projected to a common shape (city,
        region, country, processes, status, url). Cross-source filters
        (country/city/process/source/status) hard-exclude; local-only filters
        (region/access_type) soft-filter — spaces that can't express the axis are
        kept, flagged ``ambiguous``, and sorted last. Local facilities without
        coordinates are counted (``dropped_no_coords``) rather than plotted. MoM
        comes from a 24h TTL cache and degrades gracefully (``mom_available``).

        Returns:
            Dict with ``spaces`` (filtered/ranked), ``total``, per-source counts,
            ``dropped_no_coords``, and ``mom_available``.
        """
        candidates, dropped_no_coords, mom_available = (
            await self._load_network_candidates(
                include_mom=include_mom, force_refresh=force_refresh
            )
        )
        filtered = filter_network_spaces(
            candidates,
            country=country,
            city=city,
            process=process,
            source=source,
            status=status,
            region=region,
            access_type=access_type,
        )
        # Strip the internal facility back-reference from the browse payload.
        spaces = [{k: v for k, v in sp.items() if k != "_facility"} for sp in filtered]
        return {
            "spaces": spaces,
            "total": len(spaces),
            "local_count": sum(1 for s in spaces if s["source"] == "local"),
            "mom_count": sum(1 for s in spaces if s["source"] == "mom"),
            "dropped_no_coords": dropped_no_coords,
            "mom_available": mom_available,
        }

    async def _load_network_candidates(
        self, *, include_mom: bool, force_refresh: bool, require_coords: bool = True
    ) -> Tuple[List[Dict[str, Any]], int, bool]:
        """Load local ∪ MoM as unified space dicts, each carrying its ``_facility``
        (the matchable object) under a private key. Shared by the browse surface
        and the network-match candidate pool so filtering stays identical.

        ``require_coords`` gates whether local facilities without plottable
        coordinates are dropped — True for the map/browse surface, False for
        matching (where geography is not required to be a valid candidate).
        """
        candidates: List[Dict[str, Any]] = []
        dropped_no_coords = 0
        page = 1
        page_size = 500
        while True:
            facilities, _ = await self.list(page=page, page_size=page_size)
            if not facilities:
                break
            for f in facilities:
                space = _local_facility_to_space(f, require_coords=require_coords)
                if space is None:
                    dropped_no_coords += 1
                    continue
                space["_facility"] = f
                candidates.append(space)
            if len(facilities) < page_size:
                break
            page += 1

        mom_available = False
        if include_mom:
            from .mom_bridge import mom_spaces_cache

            raw, mom_available = await mom_spaces_cache.get(force_refresh=force_refresh)
            for s in raw:
                space = _mom_space_to_space(s)
                space["_facility"] = _mom_stub_facility(s)
                candidates.append(space)

        return candidates, dropped_no_coords, mom_available

    async def get_network_match_facilities(
        self,
        *,
        include_mom: bool = True,
        force_refresh: bool = False,
        require_coords: bool = True,
        country: Optional[str] = None,
        city: Optional[str] = None,
        process: Optional[str] = None,
        source: Optional[str] = None,
        status: Optional[str] = None,
        region: Optional[str] = None,
        access_type: Optional[str] = None,
    ) -> List[ManufacturingFacility]:
        """Return the filtered network as matchable facilities (local full objects
        ∪ MoM process stubs), for matching a design against the same filtered set
        the browse surface shows. Uses the identical filter as ``get_network_spaces``.

        ``require_coords`` defaults True (browse parity); the match resolver passes
        False so coordinate-less facilities remain matchable candidates.
        """
        candidates, _, _ = await self._load_network_candidates(
            include_mom=include_mom,
            force_refresh=force_refresh,
            require_coords=require_coords,
        )
        filtered = filter_network_spaces(
            candidates,
            country=country,
            city=city,
            process=process,
            source=source,
            status=status,
            region=region,
            access_type=access_type,
        )
        return [sp["_facility"] for sp in filtered]

    async def list_kitchens(self) -> List[KitchenCapability]:
        """Return all kitchen capabilities found under the ``okw/`` prefix.

        Returns only ``KitchenCapability`` objects.  Any file under
        ``okw/`` that is *not* identified as cooking capability by
        ``KitchenCapability.is_cooking_capability()`` (e.g. a manufacturing
        facility file) is skipped and logged at DEBUG level.

        Mirrors the structure of ``list()`` but:
        - Only returns files that pass ``KitchenCapability.is_cooking_capability()``.
        - Deduplicates by ``KitchenCapability.id``, keeping the most-recently
          modified file when the same ID appears at multiple paths.
        """
        await self.ensure_initialized()
        logger.info("Listing kitchen capabilities")

        if not self.storage:
            return []

        discovery = SmartFileDiscovery(self.storage.manager)
        file_infos = await discovery.discover_files("okw")

        logger.info(f"Scanning {len(file_infos)} OKW files for kitchen capabilities")

        kitchens_by_id: Dict[UUID, KitchenCapability] = {}
        file_info_by_id: Dict[UUID, Any] = {}

        for file_info in file_infos:
            try:
                data = await self.storage.manager.get_object(file_info.key)
                content = data.decode("utf-8")
                raw = json.loads(content)

                if not KitchenCapability.is_cooking_capability(raw):
                    logger.debug(
                        f"Skipping non-kitchen file {file_info.key} in list_kitchens()"
                    )
                    continue

                kitchen = KitchenCapability.from_dict(raw)
                kitchen_id = kitchen.id

                if kitchen_id not in kitchens_by_id:
                    kitchens_by_id[kitchen_id] = kitchen
                    file_info_by_id[kitchen_id] = file_info
                else:
                    existing_modified = (
                        file_info_by_id[kitchen_id].last_modified
                        if hasattr(file_info_by_id[kitchen_id], "last_modified")
                        else None
                    )
                    current_modified = (
                        file_info.last_modified
                        if hasattr(file_info, "last_modified")
                        else None
                    )
                    if current_modified and (
                        not existing_modified or current_modified > existing_modified
                    ):
                        kitchens_by_id[kitchen_id] = kitchen
                        file_info_by_id[kitchen_id] = file_info
                        logger.debug(
                            f"Replacing kitchen {kitchen_id} with more recent version from {file_info.key}"
                        )
            except Exception as e:
                logger.warning(
                    f"Skipping file {file_info.key}: could not parse as KitchenCapability: {e}"
                )
                continue

        kitchens = list(kitchens_by_id.values())
        logger.info(f"Found {len(kitchens)} unique kitchen capabilities")
        return kitchens

    async def update(
        self, facility_id: UUID, facility_data: Dict[str, Any]
    ) -> ManufacturingFacility:
        """Update a manufacturing facility in-place at its existing storage key.

        Args:
            facility_id: Facility UUID to replace.
            facility_data: Replacement facility payload.

        Returns:
            Parsed and persisted ``ManufacturingFacility`` instance.

        Notes:
            If no existing key is discovered, falls back to ``okw/{facility_id}.json``
            and logs a warning.
        """
        await self.ensure_initialized()
        logger.info(f"Updating manufacturing facility with ID {facility_id}")

        facility = ManufacturingFacility.from_dict(facility_data)

        if self.storage and self.storage.manager:
            # Discover the existing file so we overwrite at the same key,
            # preserving any user-defined subdirectory organisation under okw/.
            existing_key = await self._find_key_for_id(facility_id)

            if existing_key is None:
                existing_key = f"okw/{str(facility_id)}.json"
                logger.warning(
                    f"OKW facility {facility_id} not found during update; "
                    f"writing to fallback key {existing_key}"
                )

            facility_json = json.dumps(
                facility.to_dict(), indent=2, ensure_ascii=False, default=str
            )
            await self.storage.manager.put_object(
                existing_key, facility_json.encode("utf-8")
            )
            logger.info(f"Updated OKW facility at {existing_key}")

        return facility

    async def delete(self, facility_id: UUID) -> bool:
        """Delete a manufacturing facility by locating its actual storage key.

        Args:
            facility_id: Facility UUID to delete.

        Returns:
            ``True`` when an object was deleted; ``False`` when no key is found
            or storage is unavailable.
        """
        await self.ensure_initialized()
        logger.info(f"Deleting manufacturing facility with ID {facility_id}")

        if self.storage and self.storage.manager:
            existing_key = await self._find_key_for_id(facility_id)

            if existing_key is None:
                logger.warning(
                    f"OKW facility {facility_id} not found for deletion; "
                    "no file deleted"
                )
                return False

            result = await self.storage.manager.delete_object(existing_key)
            logger.info(f"Deleted OKW facility at {existing_key}")
            return result

        return False

    async def _find_key_for_id(self, target_id: UUID) -> Optional[str]:
        """Discover the storage key for an OKW object id.

        Args:
            target_id: UUID to match against the stored JSON ``id`` field.

        Returns:
            Matching object key or ``None`` if no key can be resolved.
        """
        discovery = SmartFileDiscovery(self.storage.manager)
        file_infos = await discovery.discover_files("okw")

        for file_info in file_infos:
            try:
                data = await self.storage.manager.get_object(file_info.key)
                content = data.decode("utf-8")
                obj_data = json.loads(content)
                if obj_data.get("id") == str(target_id):
                    return file_info.key
            except Exception as e:
                logger.debug(f"Could not read {file_info.key} during key lookup: {e}")
                continue

        return None

    async def validate(
        self,
        content: Dict[str, Any],
        validation_context: Optional[str] = None,
        strict_mode: bool = False,
    ) -> Dict[str, Any]:
        """Validate raw OKW facility content against canonical model rules.

        Args:
            content: Facility payload to validate.
            validation_context: Optional quality profile (``hobby``, ``professional``,
                or ``medical``). Unknown values default to ``professional``.
            strict_mode: Enables stricter validation semantics in the shared validator.

        Returns:
            Backward-compatible validation response including flags, issues,
            warnings, and score fields.

        Raises:
            ValueError: If validation infrastructure fails unexpectedly.
        """
        await self.ensure_initialized()
        logger.info(f"Validating OKW facility content")

        try:
            # Use common validation utility that validates against canonical ManufacturingFacility dataclass
            from ..validation.model_validator import validate_okw_facility

            quality_level = (
                validation_context
                if validation_context in ["hobby", "professional", "medical"]
                else "professional"
            )

            validation_result = validate_okw_facility(
                content=content, quality_level=quality_level, strict_mode=strict_mode
            )

            # Convert to service response format (for backward compatibility)
            return {
                "is_valid": validation_result.valid,
                "valid": validation_result.valid,  # Alias for backward compatibility
                "score": validation_result.details.get("completeness_score", 1.0),
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "suggestions": validation_result.suggestions,
                "completeness_score": validation_result.details.get(
                    "completeness_score", 1.0
                ),
                "issues": [
                    {
                        "severity": "error",
                        "message": error,
                        "path": [],
                        "code": VALIDATION_ERROR_CODE,
                    }
                    for error in validation_result.errors
                ]
                + [
                    {
                        "severity": "warning",
                        "message": warning,
                        "path": [],
                        "code": VALIDATION_WARNING_CODE,
                    }
                    for warning in validation_result.warnings
                ],
            }

        except Exception as e:
            self.logger.error(f"Error validating OKW facility: {str(e)}", exc_info=True)
            raise ValueError(f"Validation failed: {str(e)}")

    # LLM Integration Methods
    async def prepare_llm_integration(self) -> None:
        """Prepare optional LLM-related integrations for OKW workflows."""
        await super().prepare_llm_integration()

        if self.is_llm_enabled():
            self.logger.info(
                "Preparing OKW service for LLM-enhanced facility management"
            )
            # Future: Initialize LLM-specific components for facility operations
            # - LLM validation rules for facility data
            # - LLM-enhanced facility matching and recommendations
            # - LLM-powered facility capability analysis

    async def handle_llm_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle placeholder LLM request types for OKW operations.

        Args:
            request_data: Request payload containing at least ``type``.

        Returns:
            Placeholder status response for known request types, or an ``error`` payload
            for unknown request types.

        Raises:
            RuntimeError: If LLM integration is disabled in service configuration.
        """
        if not self.is_llm_enabled():
            raise RuntimeError("LLM integration not enabled for OKW service")

        request_type = request_data.get("type")

        if request_type == "validate_facility":
            # Future: Use LLM to validate facility data and capabilities
            return {"status": "llm_validation_not_implemented"}
        elif request_type == "analyze_capabilities":
            # Future: Use LLM to analyze facility capabilities
            return {"status": "llm_analysis_not_implemented"}
        elif request_type == "recommend_facilities":
            # Future: Use LLM to recommend facilities for specific requirements
            return {"status": "llm_recommendation_not_implemented"}
        else:
            return {"error": f"Unknown LLM request type: {request_type}"}

    async def _ensure_domains_registered(self) -> None:
        """Register cooking/manufacturing domains when startup registration was skipped.

        This method is best-effort for local/CLI fallback paths and logs failures instead
        of raising so service startup can continue in degraded mode.
        """
        from ..registry.domain_registry import (
            DomainMetadata,
            DomainRegistry,
            DomainStatus,
        )

        # Check if all required domains are already registered
        required_domains = {"manufacturing", "cooking"}
        registered_domains = set(DomainRegistry.list_domains())
        if required_domains.issubset(registered_domains):
            logger.info("All required domains already registered")
            return

        logger.info("Registering domains for fallback mode...")

        try:
            # Import domain components
            from ..domains.cooking.extractors import CookingExtractor
            from ..domains.cooking.matchers import CookingMatcher
            from ..domains.cooking.validation.compatibility import (
                CookingValidatorCompat,
            )
            from ..domains.manufacturing.okh_extractor import OKHExtractor
            from ..domains.manufacturing.okh_matcher import OKHMatcher
            from ..domains.manufacturing.validation.compatibility import (
                ManufacturingOKHValidatorCompat,
            )

            # Register Cooking domain
            cooking_metadata = DomainMetadata(
                name="cooking",
                display_name="Cooking & Food Preparation",
                description="Domain for recipe and kitchen capability matching",
                version="1.0.0",
                status=DomainStatus.ACTIVE,
                supported_input_types={"recipe", "kitchen"},
                supported_output_types={"cooking_workflow", "meal_plan"},
                documentation_url="https://docs.ohm.org/domains/cooking",
                maintainer="OHM Cooking Team",
            )

            DomainRegistry.register_domain(
                domain_name="cooking",
                extractor=CookingExtractor(),
                matcher=CookingMatcher(),
                validator=CookingValidatorCompat(),
                metadata=cooking_metadata,
            )

            # Register Manufacturing domain
            manufacturing_metadata = DomainMetadata(
                name="manufacturing",
                display_name="Manufacturing & Hardware Production",
                description="Domain for OKH/OKW manufacturing capability matching",
                version="1.0.0",
                status=DomainStatus.ACTIVE,
                supported_input_types={"okh", "okw"},
                supported_output_types={"supply_tree", "manufacturing_plan"},
                documentation_url="https://docs.ohm.org/domains/manufacturing",
                maintainer="OHM Manufacturing Team",
            )

            DomainRegistry.register_domain(
                domain_name="manufacturing",
                extractor=OKHExtractor(),
                matcher=OKHMatcher(),
                validator=ManufacturingOKHValidatorCompat(),
                metadata=manufacturing_metadata,
            )

            logger.info("Successfully registered domains for fallback mode")

        except Exception as e:
            logger.error(f"Failed to register domains for fallback mode: {e}")
            # Don't raise the exception - let the service continue without domains


async def resolve_match_facilities(
    *,
    effective_source: str,
    domain: str = "manufacturing",
    request_id: str = "",
    force_refresh: bool = False,
    country: Optional[str] = None,
    city: Optional[str] = None,
    process: Optional[str] = None,
    status: Optional[str] = None,
    region: Optional[str] = None,
    access_type: Optional[str] = None,
) -> List[ManufacturingFacility]:
    """Resolve the manufacturing match candidate pool for an effective source.

    The one facility-pool resolver shared by the API match route and the CLI
    (structural parity, not copy-paste). ``effective_source`` is the already
    env+request-reconciled value (see
    :func:`src.config.storage_config.resolve_effective_source`):

    - ``"mom"``    → Maps of Making only. An explicit request for MoM data, so it
      wins over ``MATCHING_LOCAL_OKW_JSON_DIR`` (a local-storage dev convenience),
      keeping API and CLI identical.
    - ``"storage"`` → blob storage only (``include_mom=False``); honours
      ``MATCHING_LOCAL_OKW_JSON_DIR`` when set.
    - ``"union"``  → storage ∪ MoM; ``MATCHING_LOCAL_OKW_JSON_DIR`` forces
      storage-only (a local dir is never unioned with MoM).

    The service instance is only loaded for the branches that read from storage,
    so the local-dir path touches no remote storage. Facilities are matched
    regardless of geography (``require_coords=False``).
    """
    if effective_source == "mom":
        svc = await OKWService.get_instance()
        return await svc.get_network_match_facilities(
            include_mom=True,
            source="mom",
            force_refresh=force_refresh,
            require_coords=False,
            country=country,
            city=city,
            process=process,
            status=status,
            region=region,
            access_type=access_type,
        )

    local_dir = resolve_matching_local_okw_json_dir()
    if local_dir:
        return load_facilities_from_local_okw_json_dir(local_dir, domain, request_id)

    svc = await OKWService.get_instance()
    return await svc.get_network_match_facilities(
        include_mom=(effective_source == "union"),
        force_refresh=force_refresh,
        require_coords=False,
        country=country,
        city=city,
        process=process,
        status=status,
        region=region,
        access_type=access_type,
    )
