import json
import traceback
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
from uuid import UUID

import httpx
import yaml

from src.config import settings

# Lazy import: GenerationEngine imports heavy dependencies (spacy, numpy, thinc)
# from ..generation.engine import GenerationEngine
from ..generation.models import LayerConfig, PlatformType
from ..generation.platforms.github import GitHubExtractor
from ..generation.platforms.gitlab import GitLabExtractor
from ..generation.url_router import URLRouter
from ..models.okh import OKHManifest, ProcessRequirement
from ..models.provenance import RecordProvenance, apply_ohm_metadata
from ..models.visibility import (
    DEFAULT_VISIBILITY,
    LEGACY_VISIBILITY,
    VisibilityLevel,
)
from ..storage.provenance_store import ProvenanceStore
from ..storage.visibility_store import VisibilityStore
from ..storage.smart_discovery import (
    FileInfo,
    SmartFileDiscovery,
    minimal_okh_manifest_dict,
)
from ..utils.logging import get_logger
from ..validation.error_codes import VALIDATION_ERROR_CODE, VALIDATION_WARNING_CODE
from ..validation.uuid_validator import UUIDValidator
from .base import BaseService, ServiceConfig
from .storage_service import StorageService

if TYPE_CHECKING:
    from ..generation.engine import GenerationEngine

logger = get_logger(__name__)


class OKHService(BaseService["OKHService"]):
    """
    Service for managing OKH manifests.

    This service provides functionality for:
    - Creating, reading, updating, and deleting OKH manifests
    - Validating OKH manifest data
    - Generating OKH manifests from project URLs
    - Managing OKH manifest storage and retrieval
    - Integration with generation engine for manifest creation
    """

    def __init__(
        self, service_name: str = "OKHService", config: Optional[ServiceConfig] = None
    ) -> None:
        """Initialize the OKH service with base service functionality."""
        super().__init__(service_name, config)
        self.storage: Optional[StorageService] = None
        self.generation_engine: Optional[GenerationEngine] = None
        self.url_router: Optional[URLRouter] = None

    async def _initialize_dependencies(self) -> None:
        """Initialize storage, generation engine, and URL routing dependencies.

        This method is invoked by :class:`BaseService` during first-time initialization.
        """
        # Initialize storage service
        self.storage = await StorageService.get_instance()

        # Configure storage service if not already configured
        if self.storage and not self.storage._configured:
            await self.storage.configure(settings.STORAGE_CONFIG)

        # Initialize generation engine lazily (only when needed)
        # Lazy import to avoid loading heavy dependencies (spacy, numpy, thinc) at module import time
        from ..generation.engine import GenerationEngine

        self.generation_engine = GenerationEngine()

        # Initialize URL router
        self.url_router = URLRouter()

        self.logger.info("OKH service dependencies initialized")

    async def initialize(self) -> None:
        """Load storage and generation dependencies and register them on the base service."""
        await self.ensure_initialized()

        # Add dependencies to base service
        self.add_dependency("storage", self.storage)
        self.add_dependency("generation_engine", self.generation_engine)
        self.add_dependency("url_router", self.url_router)

        self.logger.info("OKH service initialized successfully")

    async def create(
        self,
        manifest_data: Dict[str, Any],
        created_by: Optional[str] = None,
        provenance: Optional[RecordProvenance] = None,
    ) -> OKHManifest:
        """Persist a new manifest under ``okh/`` when storage is available.

        Args:
            manifest_data: Raw dict or pass-through if already an ``OKHManifest``.
            created_by: Optional account id to attribute the record to; persisted
                alongside the manifest JSON (see federated-identity Slice 1).
            provenance: Optional record-level authorship/publication provenance
                (federated-identity Slice 3).

        New records stamp ``private`` visibility (Slice 4); promote with
        :meth:`set_visibility` to share via the federation catalog.

        Returns:
            The created ``OKHManifest`` instance (with generated id if applicable).
        """
        async with self.track_request("create_okh_manifest"):
            await self.ensure_initialized()
            self.logger.info("Creating new OKH manifest")

            # Create manifest object - handle both dict and OKHManifest inputs
            if isinstance(manifest_data, OKHManifest):
                manifest = manifest_data
            else:
                manifest = OKHManifest.from_dict(manifest_data)

            # Store directly under okh/ with a human-readable, ID-anchored filename.
            # No subdirectory is enforced; users may organise beneath okh/ freely.
            if self.storage and self.storage.manager:
                safe_title = "".join(
                    c for c in manifest.title if c.isalnum() or c in (" ", "-", "_")
                ).rstrip()
                safe_title = safe_title.replace(" ", "-").lower()
                filename = f"okh/{safe_title}-{str(manifest.id)[:8]}-okh.json"

                # OHM-namespaced metadata (account attribution) is carried through
                # explicitly because to_dict() is a whitelist that drops ohm_* keys —
                # this is what lets ohm_created_by survive a federation ingest.
                payload = apply_ohm_metadata(
                    manifest.to_dict(), manifest_data, created_by
                )
                manifest_json = json.dumps(
                    payload, indent=2, ensure_ascii=False, default=str
                )
                await self.storage.manager.put_object(
                    filename, manifest_json.encode("utf-8")
                )
                self.logger.info(f"Saved OKH manifest to {filename}")

                # Provenance + visibility live in their own planes (out of the
                # content hash). Visibility defaults to private — opt-in to share.
                if provenance is not None:
                    await self._provenance_store().save(str(manifest.id), provenance)
                await self._visibility_store().save(
                    str(manifest.id), DEFAULT_VISIBILITY
                )

            return manifest

    def _provenance_store(self) -> ProvenanceStore:
        """Lazily build the provenance store over the configured storage."""
        return ProvenanceStore(self.storage)

    def _visibility_store(self) -> VisibilityStore:
        """Lazily build the visibility store over the configured storage."""
        return VisibilityStore(self.storage)

    async def get_provenance(self, manifest_id: UUID) -> Optional[RecordProvenance]:
        """Return the stored provenance for a manifest, or None."""
        await self.ensure_initialized()
        if not self.storage or not self.storage.manager:
            return None
        return await self._provenance_store().load(str(manifest_id))

    async def get_visibility(self, manifest_id: UUID) -> VisibilityLevel:
        """Return visibility for a manifest.

        Missing (pre-Slice-4) records resolve to ``followers`` so they keep
        appearing in the catalog; new creates stamp ``private`` explicitly.
        """
        await self.ensure_initialized()
        if not self.storage or not self.storage.manager:
            return LEGACY_VISIBILITY
        loaded = await self._visibility_store().load(str(manifest_id))
        return loaded if loaded is not None else LEGACY_VISIBILITY

    async def set_visibility(
        self, manifest_id: UUID, level: VisibilityLevel
    ) -> VisibilityLevel:
        """Set share policy for a manifest. Record must already exist."""
        await self.ensure_initialized()
        if not self.storage or not self.storage.manager:
            raise RuntimeError("Storage service not available")
        if await self.get(manifest_id) is None:
            raise LookupError(f"OKH manifest {manifest_id} not found")
        await self._visibility_store().save(str(manifest_id), level)
        return level

    async def get(self, manifest_id: UUID) -> Optional[OKHManifest]:
        """Scan discovered ``okh/`` objects and return the first manifest whose id matches.

        Args:
            manifest_id: Target manifest UUID.

        Returns:
            Parsed ``OKHManifest``, or ``None`` if storage is unavailable or no file matches.
        """
        async with self.track_request("get_okh_manifest"):
            try:
                await self.ensure_initialized()
                self.logger.info(f"Getting OKH manifest with ID {manifest_id}")

                if not self.storage or not self.storage.manager:
                    self.logger.error("Storage service not available or not configured")
                    return None

                self.logger.info(
                    "Storage service is available, searching for OKH files..."
                )

                # Use smart discovery to find OKH files
                discovery = SmartFileDiscovery(self.storage.manager)
                file_infos = await discovery.discover_files("okh")

                self.logger.info(
                    f"Found {len(file_infos)} OKH files using smart discovery"
                )

                # Search through OKH files for the matching ID
                for file_info in file_infos:
                    try:
                        data = await self.storage.manager.get_object(file_info.key)
                        content = data.decode("utf-8")
                        okh_data = json.loads(content)

                        self.logger.debug(
                            f"Loaded OKH data from {file_info.key}, ID: {okh_data.get('id')}"
                        )

                        # Validate and fix UUID issues
                        fixed_okh_data = UUIDValidator.validate_and_fix_okh_data(
                            okh_data
                        )

                        # Check if this is the manifest we're looking for
                        if fixed_okh_data.get("id") == str(manifest_id):
                            self.logger.info(
                                f"Found matching OKH manifest in {file_info.key}"
                            )
                            manifest = OKHManifest.from_dict(fixed_okh_data)
                            self.logger.info(
                                f"Successfully created OKHManifest object for {manifest.title}"
                            )
                            return manifest
                        else:
                            self.logger.debug(
                                f"ID mismatch: looking for {manifest_id}, found {fixed_okh_data.get('id')}"
                            )

                    except Exception as e:
                        self.logger.error(
                            f"Failed to load OKH file {file_info.key}: {e}"
                        )
                        self.logger.error(f"Traceback: {traceback.format_exc()}")
                        continue

                self.logger.warning(
                    f"OKH manifest with ID {manifest_id} not found. Searched {len(file_infos)} OKH files"
                )
                return None

            except Exception as e:
                self.logger.error(f"Unexpected error in get method: {e}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                raise

    async def get_by_id(self, manifest_id: UUID) -> Optional[OKHManifest]:
        """Compatibility alias for :meth:`get`.

        Args:
            manifest_id: Target manifest UUID.

        Returns:
            Matching manifest or ``None`` when not found.
        """
        return await self.get(manifest_id)

    async def fetch_from_url(self, url: str) -> OKHManifest:
        """HTTP GET a remote manifest and parse YAML or JSON into ``OKHManifest``.

        Args:
            url: Document location (content-type or extension hints YAML vs JSON).

        Returns:
            Parsed in-memory manifest (not automatically written to storage).

        Raises:
            ValueError: On parse failure or transport errors (wrapped from ``httpx``).
        """
        async with self.track_request("fetch_okh_from_url"):
            await self.ensure_initialized()
            self.logger.info(f"Fetching OKH manifest from URL: {url}")

            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.get(url)
                    response.raise_for_status()

                    # Try to parse as YAML first, then JSON
                    content = response.text
                    try:
                        if (
                            url.endswith(".yaml")
                            or url.endswith(".yml")
                            or "yaml" in response.headers.get("content-type", "")
                        ):
                            data = yaml.safe_load(content)
                        else:
                            data = json.loads(content)
                    except (yaml.YAMLError, json.JSONDecodeError) as e:
                        self.logger.error(f"Failed to parse manifest content: {e}")
                        raise ValueError(f"Invalid manifest format: {e}")

                    # Create manifest object
                    manifest = OKHManifest.from_dict(data)
                    self.logger.info(
                        f"Successfully fetched OKH manifest: {manifest.id}"
                    )
                    return manifest

            except httpx.HTTPError as e:
                self.logger.error(f"HTTP error fetching manifest from {url}: {e}")
                raise ValueError(f"Failed to fetch manifest from URL: {e}")
            except Exception as e:
                self.logger.error(f"Error fetching manifest from {url}: {e}")
                raise ValueError(f"Error fetching manifest: {e}")

    async def list(
        self,
        page: int = 1,
        page_size: int = 100,
        filter_params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[OKHManifest], int]:
        """Return a page of minimal OKH manifests discovered under the ``okh/`` prefix.

        Args:
            page: 1-based page index.
            page_size: Page length.
            filter_params: Reserved for future filtering (currently unused).

        Returns:
            ``(manifests, total_count)`` after deduplication by manifest id (newest file wins).
        """
        async with self.track_request("list_okh_manifests"):
            await self.ensure_initialized()
            self.logger.info(
                f"Listing OKH manifests (page={page}, page_size={page_size})"
            )

            if not self.storage or not self.storage.manager:
                self.logger.warning("Storage service not available or not configured")
                return [], 0

            # Use smart discovery to find OKH files
            discovery = SmartFileDiscovery(self.storage.manager)
            file_infos = await discovery.discover_files("okh")

            self.logger.info(f"Found {len(file_infos)} OKH files using smart discovery")

            # Load and deduplicate manifests by ID (keep most recent)
            manifest_map: Dict[UUID, Tuple[FileInfo, OKHManifest]] = {}
            for file_info in file_infos:
                try:
                    data = await self.storage.manager.get_object(file_info.key)
                    content = data.decode("utf-8")
                    okh_data = json.loads(content)

                    # Validate and fix UUID issues
                    fixed_okh_data = UUIDValidator.validate_and_fix_okh_data(okh_data)
                    if not minimal_okh_manifest_dict(fixed_okh_data):
                        self.logger.warning(
                            "Skipping OKH storage key %s: not a minimal OKH manifest "
                            "(e.g. standalone BOM JSON or incomplete file)",
                            file_info.key,
                        )
                        continue
                    manifest = OKHManifest.from_dict(fixed_okh_data)

                    # Deduplicate by ID, keeping the most recently modified
                    if manifest.id not in manifest_map:
                        manifest_map[manifest.id] = (file_info, manifest)
                    else:
                        existing_file_info, _ = manifest_map[manifest.id]
                        if hasattr(file_info, "last_modified") and hasattr(
                            existing_file_info, "last_modified"
                        ):
                            if (
                                file_info.last_modified
                                > existing_file_info.last_modified
                            ):
                                manifest_map[manifest.id] = (file_info, manifest)
                                self.logger.debug(
                                    f"Replacing duplicate manifest {manifest.id} with more recent version from {file_info.key}"
                                )
                except Exception as e:
                    self.logger.error(f"Failed to load OKH file {file_info.key}: {e}")
                    continue

            # Convert to list and apply pagination
            all_manifests = [manifest for _, manifest in manifest_map.values()]
            total = len(all_manifests)

            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_manifests = all_manifests[start_idx:end_idx]

            return paginated_manifests, total

    async def list_manifests(
        self, limit: int = 100, offset: int = 0
    ) -> List[OKHManifest]:
        """List OKH manifests with ``limit``/``offset`` (maps internally to :meth:`list`)."""
        # Convert limit/offset to page/page_size
        page_size = limit
        page = (offset // page_size) + 1

        manifests, total = await self.list(page=page, page_size=page_size)
        return manifests

    async def update(
        self, manifest_id: UUID, manifest_data: Dict[str, Any]
    ) -> OKHManifest:
        """Update an OKH manifest in-place at its existing storage key.

        Args:
            manifest_id: Manifest UUID to replace.
            manifest_data: Replacement manifest payload.

        Returns:
            Parsed and persisted ``OKHManifest`` instance.

        Notes:
            If the original key cannot be discovered, the service falls back to
            ``okh/{manifest_id}.json`` and logs a warning.
        """
        await self.ensure_initialized()
        logger.info(f"Updating OKH manifest with ID {manifest_id}")

        manifest = OKHManifest.from_dict(manifest_data)

        if self.storage and self.storage.manager:
            # Discover the existing file so we overwrite at the same key,
            # preserving any user-defined subdirectory organisation under okh/.
            existing_key = await self._find_key_for_id(manifest_id, "okh")

            if existing_key is None:
                # Fallback: write to a canonical flat key and log the miss.
                existing_key = f"okh/{str(manifest_id)}.json"
                logger.warning(
                    f"OKH manifest {manifest_id} not found during update; "
                    f"writing to fallback key {existing_key}"
                )

            manifest_json = json.dumps(
                manifest.to_dict(), indent=2, ensure_ascii=False, default=str
            )
            await self.storage.manager.put_object(
                existing_key, manifest_json.encode("utf-8")
            )
            logger.info(f"Updated OKH manifest at {existing_key}")

        return manifest

    async def import_repair_doc(
        self,
        result: Any,
        manifest_id: Optional[UUID] = None,
        title: Optional[str] = None,
    ) -> OKHManifest:
        """Merge repair extraction output into a manifest with conservative defaults.

        For each extracted component:
        - If a component with the same name already exists: preserve all existing
          flags (replaceable, salvageable, consumable); update part_number only if
          currently unset; append new diagnostic_codes and failure_modes.
        - If the component is new: import with replaceable=False, salvageable=False
          regardless of what the extractor inferred, to require human annotation.

        For repair guides: deduplicate by title; append new ones.

        If ``manifest_id`` is given, patches the existing manifest. Otherwise creates
        a new manifest using ``title`` for its title field.
        """
        await self.ensure_initialized()
        from ..models.okh import Component

        if manifest_id is not None:
            manifest = await self.get(manifest_id)
            if manifest is None:
                raise KeyError(f"OKH manifest {manifest_id} not found")
        else:
            if not title:
                raise ValueError("title is required when creating a new manifest")
            manifest = OKHManifest.from_dict(
                {
                    "title": title,
                    "version": "0.1.0",
                    "license": {"hardware": "CERN-OHL-S-2.0"},
                    "licensor": "Imported",
                    "documentation_language": "en",
                    "function": f"Imported from {', '.join(result.source_files)}",
                }
            )

        # Merge components by name
        existing: Dict[str, Any] = {
            c.name.lower(): c for c in (manifest.components or [])
        }
        for extracted in result.components:
            key = extracted.name.lower()
            if key in existing:
                comp = existing[key]
                # Preserve existing repair flags; only fill genuinely missing data
                if not comp.part_number and extracted.part_number:
                    comp.part_number = extracted.part_number
                for code in extracted.diagnostic_codes or []:
                    if code not in (comp.diagnostic_codes or []):
                        comp.diagnostic_codes = (comp.diagnostic_codes or []) + [code]
                for mode in extracted.failure_modes or []:
                    if mode not in (comp.failure_modes or []):
                        comp.failure_modes = (comp.failure_modes or []) + [mode]
            else:
                existing[key] = Component(
                    name=extracted.name,
                    part_number=extracted.part_number,
                    consumable=extracted.consumable,
                    # Conservative defaults — human must annotate before triage
                    replaceable=False,
                    salvageable=False,
                    diagnostic_codes=extracted.diagnostic_codes or [],
                    failure_modes=extracted.failure_modes or [],
                    repair_notes=extracted.repair_notes,
                )
        manifest.components = list(existing.values())

        # Merge repair guides by title (dedup)
        existing_guide_titles = {
            g.title.lower() for g in (manifest.repair_guides or [])
        }
        for guide in result.repair_guides or []:
            if guide.title.lower() not in existing_guide_titles:
                manifest.repair_guides = (manifest.repair_guides or []) + [guide]
                existing_guide_titles.add(guide.title.lower())

        if manifest_id is not None:
            return await self.update(manifest_id, manifest.to_dict())
        return await self.create(manifest.to_dict())

    async def delete(self, manifest_id: UUID) -> bool:
        """Delete an OKH manifest by locating its actual storage key.

        Args:
            manifest_id: Manifest UUID to delete.

        Returns:
            ``True`` when an object was deleted; ``False`` when no matching key is found
            or storage is unavailable.
        """
        await self.ensure_initialized()
        logger.info(f"Deleting OKH manifest with ID {manifest_id}")

        if self.storage and self.storage.manager:
            existing_key = await self._find_key_for_id(manifest_id, "okh")

            if existing_key is None:
                logger.warning(
                    f"OKH manifest {manifest_id} not found for deletion; "
                    "no file deleted"
                )
                return False

            result = await self.storage.manager.delete_object(existing_key)
            logger.info(f"Deleted OKH manifest at {existing_key}")
            return result

        return False

    async def _find_key_for_id(self, target_id: UUID, file_type: str) -> Optional[str]:
        """Discover a storage key by object id under a logical file type prefix.

        Args:
            target_id: UUID to match against the stored JSON ``id`` field.
            file_type: Prefix bucket segment to scan (for example ``okh``).

        Returns:
            Matching object key or ``None`` when no key can be resolved.
        """
        discovery = SmartFileDiscovery(self.storage.manager)
        file_infos = await discovery.discover_files(file_type)

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

    async def extract_requirements(self, manifest_id: UUID) -> List[ProcessRequirement]:
        """Extract process requirements from a stored OKH manifest.

        Args:
            manifest_id: Manifest UUID to load before extraction.

        Returns:
            List of ``ProcessRequirement`` values, or an empty list when the manifest
            does not exist.
        """
        await self.ensure_initialized()
        logger.info(f"Extracting requirements from OKH manifest {manifest_id}")

        manifest = await self.get(manifest_id)
        if not manifest:
            return []

        return manifest.extract_requirements()

    async def validate(
        self,
        content: Dict[str, Any],
        validation_context: Optional[str] = None,
        strict_mode: bool = False,
    ) -> Dict[str, Any]:
        """Validate raw OKH manifest content against canonical model rules.

        Args:
            content: Manifest payload to validate.
            validation_context: Optional quality profile (``hobby``, ``professional``,
                or ``medical``). Unknown values default to ``professional``.
            strict_mode: Enables stricter validation semantics in the shared validator.

        Returns:
            Backward-compatible validation response containing validity flags,
            issues, warnings, and summary scoring fields.

        Raises:
            ValueError: If validation infrastructure fails unexpectedly.
        """
        await self.ensure_initialized()
        logger.info(f"Validating OKH manifest content")

        try:
            # Use common validation utility that validates against canonical OKHManifest dataclass
            from ..validation.model_validator import validate_okh_manifest

            quality_level = (
                validation_context
                if validation_context in ["hobby", "professional", "medical"]
                else "professional"
            )

            # Detect domain from content
            domain = None
            if isinstance(content, dict):
                domain = content.get("domain")

            validation_result = validate_okh_manifest(
                content=content,
                quality_level=quality_level,
                strict_mode=strict_mode,
                domain=domain,
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
            logger.error(f"Error validating OKH manifest: {str(e)}", exc_info=True)
            raise ValueError(f"Validation failed: {str(e)}")

    async def generate_from_url(
        self,
        url: str,
        skip_review: bool = False,
        verbose: bool = False,
        clone: bool = False,
        save_clone: Optional[str] = None,
        no_llm: bool = False,
    ) -> Dict[str, Any]:
        """Generate OKH manifest from a repository URL or a local clone path.

        Args:
            url: Remote repository URL (GitHub / GitLab) *or* an absolute path to an
                already-cloned local directory on the server filesystem.
            skip_review: Skip interactive review step.
            verbose: Include file metadata in the generated manifest.
            clone: Clone the repository locally before extraction.  Ignored when
                ``url`` is a local path.
            save_clone: Server-side path where the clone should be persisted after
                generation (only used when ``clone=True`` and ``url`` is a remote URL).
            no_llm: If True, use 3-layer generation only. If False (default), prefer
                LLM + chunked map-reduce when credentials exist; otherwise degrade to
                3-layer automatically.

        Returns:
            Response dictionary with ``success``, ``message``, generated ``manifest``,
            and a ``quality_report`` summary.

        Raises:
            ValueError: If URL/path validation, extraction, or generation fails.
        """
        try:
            await self.ensure_initialized()

            from pathlib import Path as _Path

            from ..generation.platforms.local_git import LocalGitExtractor

            # --- Local path input: skip all network extraction ---
            local_input = _Path(url)
            if local_input.is_dir():
                self.logger.info(f"Local path detected, extracting from: {local_input}")
                extractor = LocalGitExtractor()
                project_data = await extractor.extract_from_local_path(local_input)

            else:
                # --- Remote URL input ---
                router = URLRouter()
                if not router.validate_url(url):
                    raise ValueError(f"Invalid URL or path does not exist: {url}")

                platform = router.detect_platform(url)
                if platform is None:
                    raise ValueError(f"Unsupported platform for URL: {url}")

                if clone and router.supports_local_cloning(url):
                    persist_path = _Path(save_clone) if save_clone else None
                    extractor = LocalGitExtractor()
                    project_data = await extractor.extract_project(
                        url, persist_path=persist_path
                    )
                else:
                    if platform == PlatformType.GITHUB:
                        generator = GitHubExtractor()
                    elif platform == PlatformType.GITLAB:
                        generator = GitLabExtractor()
                    else:
                        raise ValueError(f"Unsupported platform: {platform}")
                    project_data = await generator.extract_project(url)

            # Generate manifest (prefer LLM + chunking unless no_llm; degrade if
            # no API keys — see LayerConfig.for_generate_from_url / is_llm_configured).
            from ..generation.engine import GenerationEngine

            config = LayerConfig.for_generate_from_url(no_llm=no_llm)
            if config.use_llm and not config.is_llm_configured():
                self.logger.info(
                    "OKH generate-from-url: LLM preferred but not configured; "
                    "using 3-layer generation (direct/heuristic/NLP)."
                )

            engine = GenerationEngine(config=config)
            result = await engine.generate_manifest_async(
                project_data, include_file_metadata=verbose
            )

            # Note: Review interface is handled by CLI, not API service

            # Convert to response format - use to_okh_manifest() to get full OKH structure
            manifest_dict = result.to_okh_manifest(include_field_confidence=verbose)

            return {
                "success": True,
                "message": "Manifest generated successfully",
                "manifest": manifest_dict,
                "quality_report": {
                    "overall_quality": result.quality_report.overall_quality,
                    "required_fields_complete": result.quality_report.required_fields_complete,
                    "missing_required_fields": result.quality_report.missing_required_fields,
                    "recommendations": result.quality_report.recommendations,
                },
            }

        except Exception as e:
            self.logger.error(f"Error generating manifest from URL {url}: {str(e)}")
            raise ValueError(f"Generation failed: {str(e)}")

    # LLM Integration Methods
    async def prepare_llm_integration(self) -> None:
        """Prepare optional LLM-related integrations for manifest workflows."""
        await super().prepare_llm_integration()

        if self.is_llm_enabled():
            self.logger.info(
                "Preparing OKH service for LLM-enhanced manifest generation"
            )
            # Future: Initialize LLM-specific components for manifest generation
            # - LLM prompt templates for manifest field generation
            # - LLM validation rules for manifest content
            # - LLM-enhanced extraction from project URLs

    async def handle_llm_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle placeholder LLM request types for OKH operations.

        Args:
            request_data: Request payload containing at least ``type``.

        Returns:
            Placeholder status response for known request types, or an ``error`` payload
            for unknown request types.

        Raises:
            RuntimeError: If LLM integration is disabled in service configuration.
        """
        if not self.is_llm_enabled():
            raise RuntimeError("LLM integration not enabled for OKH service")

        request_type = request_data.get("type")

        if request_type == "generate_manifest":
            # Future: Use LLM to enhance manifest generation
            return {"status": "llm_generation_not_implemented"}
        elif request_type == "validate_manifest":
            # Future: Use LLM to validate manifest content
            return {"status": "llm_validation_not_implemented"}
        elif request_type == "extract_from_url":
            # Future: Use LLM to extract better information from project URLs
            return {"status": "llm_extraction_not_implemented"}
        else:
            return {"error": f"Unknown LLM request type: {request_type}"}

    async def backfill_manufacturing_processes(
        self,
        *,
        manifest_ids: Optional[List[UUID]] = None,
        only_if_empty: bool = True,
        dry_run: bool = True,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Infer manufacturing_processes from file types / title on stored OKHs.

        By default only fills empty process lists and does not write (dry_run=True).
        Pass dry_run=False to persist updates via :meth:`update`.
        """
        from ..generation.services.process_inference_service import (
            ProcessInferenceService,
        )

        await self.ensure_initialized()
        service = ProcessInferenceService()

        targets: List[OKHManifest] = []
        if manifest_ids:
            for mid in manifest_ids:
                manifest = await self.get(mid)
                if manifest is None:
                    continue
                targets.append(manifest)
        else:
            page_size = limit or 500
            manifests, _total = await self.list(page=1, page_size=page_size)
            targets = manifests[:limit] if limit is not None else list(manifests)

        scanned = 0
        updated: List[Dict[str, Any]] = []
        skipped_nonempty = 0
        no_inference = 0
        missing = 0

        if manifest_ids:
            found_ids = {m.id for m in targets}
            missing = len([mid for mid in manifest_ids if mid not in found_ids])

        for manifest in targets:
            scanned += 1
            before = list(manifest.manufacturing_processes or [])
            if only_if_empty and before:
                skipped_nonempty += 1
                continue

            result = service.apply_to_manifest(manifest, only_if_empty=only_if_empty)
            if not result.applied or not result.processes:
                if not result.applied:
                    no_inference += 1
                continue

            after = list(manifest.manufacturing_processes or [])
            entry = {
                "id": str(manifest.id),
                "title": manifest.title,
                "before": before,
                "after": after,
                "inferred": result.processes,
                "evidence": result.evidence,
            }
            if not dry_run:
                await self.update(manifest.id, manifest.to_dict())
            updated.append(entry)

        return {
            "dry_run": dry_run,
            "only_if_empty": only_if_empty,
            "scanned": scanned,
            "missing": missing,
            "skipped_nonempty": skipped_nonempty,
            "no_inference": no_inference,
            "updated_count": len(updated),
            "updated": updated,
        }

    async def cleanup(self) -> None:
        """Cleanup OKH resources and best-effort close dependency helpers."""
        await super().cleanup()

        # Cleanup generation engine if it has cleanup method
        if self.generation_engine and hasattr(self.generation_engine, "cleanup"):
            try:
                await self.generation_engine.cleanup()
                self.logger.info("Generation engine cleaned up")
            except Exception as e:
                self.logger.warning(f"Error cleaning up generation engine: {e}")

        # Cleanup URL router if it has cleanup method
        if self.url_router and hasattr(self.url_router, "cleanup"):
            try:
                await self.url_router.cleanup()
                self.logger.info("URL router cleaned up")
            except Exception as e:
                self.logger.warning(f"Error cleaning up URL router: {e}")

        self.logger.info("OKH service cleanup completed")
