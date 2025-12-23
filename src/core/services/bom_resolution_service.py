"""
BOM Resolution Service for nested supply tree generation.

This service handles loading and parsing BOMs from OKH manifests,
supporting both embedded BOMs (within manifest) and external BOM files.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import yaml

from src.config.settings import MAX_DEPTH

from ..models.bom import BillOfMaterials, Component
from ..models.component_match import ComponentMatch
from ..models.okh import OKHManifest, PartSpec
from ..services.okh_service import OKHService
from ..utils.logging import get_logger

logger = get_logger(__name__)


class BOMResolutionService:
    """Service for resolving BOMs from OKH manifests"""

    def __init__(self, okh_service: Optional[OKHService] = None):
        """Initialize BOM resolution service"""
        self.okh_service = okh_service

    def _detect_bom_type(self, okh_manifest: OKHManifest) -> str:
        """
        Detect whether BOM is embedded or external.

        Detection logic:
        - If okh_manifest.bom is a non-empty string: external BOM file
        - If okh_manifest.bom is a dict with "external_file" key: external BOM file
        - If okh_manifest.parts or okh_manifest.sub_parts have data: embedded BOM
        - Otherwise: no BOM

        Args:
            okh_manifest: OKH manifest to check

        Returns:
            "embedded", "external", or "none"
        """
        # Check for external BOM file reference
        # Handle both string path and object with external_file property
        if okh_manifest.bom:
            if isinstance(okh_manifest.bom, str) and okh_manifest.bom.strip():
                return "external"
            elif (
                isinstance(okh_manifest.bom, dict)
                and "external_file" in okh_manifest.bom
            ):
                return "external"

        # Check for embedded BOM data
        if (okh_manifest.parts and len(okh_manifest.parts) > 0) or (
            okh_manifest.sub_parts and len(okh_manifest.sub_parts) > 0
        ):
            return "embedded"

        return "none"

    def _get_external_bom_path(self, okh_manifest: OKHManifest) -> Optional[str]:
        """
        Extract external BOM file path from OKH manifest.

        Handles both:
        - String path: "bom/bom.json"
        - Object with external_file: {"external_file": "bom/bom.json", ...}

        Args:
            okh_manifest: OKH manifest with external BOM reference

        Returns:
            BOM file path string, or None if not found
        """
        if not okh_manifest.bom:
            return None

        if isinstance(okh_manifest.bom, str):
            return okh_manifest.bom.strip()
        elif isinstance(okh_manifest.bom, dict):
            external_file = okh_manifest.bom.get("external_file")
            if external_file and isinstance(external_file, str):
                return external_file.strip()

        return None

    def _resolve_bom_path(
        self, bom_path: str, manifest_path: Optional[str] = None
    ) -> str:
        """
        Resolve BOM file path relative to OKH manifest location.

        Handles:
        - Relative paths (e.g., "bom.json", "bom/bom.json")
        - Absolute paths (returns as-is)

        Args:
            bom_path: BOM file path (relative or absolute)
            manifest_path: Path to OKH manifest file (optional, for relative path resolution)

        Returns:
            Resolved BOM file path
        """
        # If path is already absolute, return as-is
        if os.path.isabs(bom_path):
            return bom_path

        # If no manifest path provided, return relative path as-is
        if not manifest_path:
            return bom_path

        # Resolve relative to manifest directory
        manifest_dir = Path(manifest_path).parent
        resolved_path = (manifest_dir / bom_path).resolve()
        return str(resolved_path)

    async def _load_external_bom(
        self,
        okh_manifest: OKHManifest,
        okh_service: Optional[OKHService] = None,
        manifest_path: Optional[str] = None,
    ) -> BillOfMaterials:
        """
        Load BOM from external file referenced by okh_manifest.bom.

        Algorithm:
        1. Get BOM file path from manifest
        2. Resolve path relative to OKH manifest location
        3. Load file content (JSON, YAML, or Markdown)
        4. Parse using BillOfMaterials.from_dict() or BOMProcessor
        5. Return BillOfMaterials

        Args:
            okh_manifest: OKH manifest with external BOM reference
            okh_service: OKHService instance for file loading (optional)
            manifest_path: Path to OKH manifest file (for path resolution)

        Returns:
            BillOfMaterials object
        """
        bom_path = self._get_external_bom_path(okh_manifest)
        if not bom_path:
            raise ValueError("No external BOM path found in manifest")

        # Resolve path relative to manifest location
        resolved_path = self._resolve_bom_path(bom_path, manifest_path)

        # Load file content
        file_content = await self._load_file_content(
            resolved_path, okh_service, manifest_path
        )

        # Parse based on file extension
        file_ext = Path(resolved_path).suffix.lower()

        if file_ext == ".json":
            bom_data = json.loads(file_content)
        elif file_ext in [".yaml", ".yml"]:
            bom_data = yaml.safe_load(file_content)
        else:
            # For other formats (e.g., .md), try to use BOMProcessor
            # For now, raise error - can be enhanced later
            raise ValueError(
                f"Unsupported BOM file format: {file_ext}. Only JSON and YAML are supported."
            )

        # Parse into BillOfMaterials
        if isinstance(bom_data, dict):
            # Check if it's already in BillOfMaterials format
            if "components" in bom_data or "name" in bom_data:
                return BillOfMaterials.from_dict(bom_data)
            else:
                raise ValueError(
                    f"Invalid BOM file format: missing 'components' or 'name' field"
                )
        else:
            raise ValueError(
                f"Invalid BOM file format: expected dict, got {type(bom_data)}"
            )

    async def _load_file_content(
        self,
        file_path: str,
        okh_service: Optional[OKHService] = None,
        manifest_path: Optional[str] = None,
    ) -> str:
        """
        Load file content from filesystem or storage.

        Args:
            file_path: Path to file (absolute or relative)
            okh_service: OKHService instance (optional, for storage-based loading)
            manifest_path: Path to manifest (optional, for relative path resolution)

        Returns:
            File content as string
        """
        # Try filesystem first
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

        # If OKHService provided and has load_file method, use it
        if okh_service and hasattr(okh_service, "load_file"):
            try:
                return await okh_service.load_file(file_path, manifest_path)
            except Exception as e:
                logger.warning(f"Failed to load file via OKHService: {e}")

        # If file doesn't exist, raise error
        raise FileNotFoundError(f"BOM file not found: {file_path}")

    async def _load_embedded_bom(self, okh_manifest: OKHManifest) -> BillOfMaterials:
        """
        Load BOM from embedded OKH manifest fields.

        Handles:
        - parts: List[PartSpec] - direct parts/components
        - sub_parts: List[Dict] - nested sub-parts (may need conversion)

        Args:
            okh_manifest: OKH manifest with embedded BOM data

        Returns:
            BillOfMaterials object with components
        """
        components = []

        # Convert parts to components
        if okh_manifest.parts:
            for part in okh_manifest.parts:
                component = self._part_to_component(part)
                components.append(component)

        # Convert sub_parts to components (may be nested)
        if okh_manifest.sub_parts:
            for sub_part in okh_manifest.sub_parts:
                component = self._sub_part_to_component(sub_part)
                components.append(component)

        return BillOfMaterials(
            name=okh_manifest.title or "Unknown", components=components
        )

    def _part_to_component(self, part: PartSpec) -> Component:
        """Convert PartSpec to Component"""
        # PartSpec doesn't have quantity/unit directly, so use defaults
        # These can be extracted from metadata or manufacturing_params if needed
        quantity = 1.0
        unit = "pieces"

        # Try to extract quantity from manufacturing_params if available
        if hasattr(part, "manufacturing_params") and part.manufacturing_params:
            if "quantity" in part.manufacturing_params:
                quantity = float(part.manufacturing_params["quantity"])
            if "unit" in part.manufacturing_params:
                unit = str(part.manufacturing_params["unit"])

        # Build requirements dict from PartSpec fields
        requirements = {}
        if hasattr(part, "material") and part.material:
            requirements["material"] = part.material
        if hasattr(part, "outer_dimensions") and part.outer_dimensions:
            requirements["dimensions"] = part.outer_dimensions
        if hasattr(part, "mass") and part.mass:
            requirements["mass"] = part.mass

        # Build metadata from PartSpec
        metadata = {}
        if hasattr(part, "tsdc") and part.tsdc:
            metadata["tsdc"] = part.tsdc
        if hasattr(part, "source") and part.source:
            metadata["source"] = (
                part.source if isinstance(part.source, list) else [part.source]
            )
        if hasattr(part, "export") and part.export:
            metadata["export"] = (
                part.export if isinstance(part.export, list) else [part.export]
            )

        return Component(
            id=str(part.id) if hasattr(part, "id") and part.id else str(uuid4()),
            name=part.name,
            quantity=quantity,
            unit=unit,
            requirements=requirements,
            metadata=metadata,
        )

    def _sub_part_to_component(self, sub_part: Dict[str, Any]) -> Component:
        """Convert sub_part Dict to Component (may be nested)"""
        # Handle nested sub_parts recursively
        sub_components = []
        if "sub_parts" in sub_part and sub_part["sub_parts"]:
            for nested_sub_part in sub_part["sub_parts"]:
                sub_components.append(self._sub_part_to_component(nested_sub_part))

        # Extract reference if present
        reference = sub_part.get("reference")

        # Build requirements from sub_part dict
        requirements = sub_part.get("requirements", {})

        # Build metadata from sub_part dict (excluding fields we've already used)
        metadata = {}
        for key, value in sub_part.items():
            if key not in [
                "name",
                "quantity",
                "unit",
                "id",
                "sub_parts",
                "reference",
                "requirements",
            ]:
                metadata[key] = value

        return Component(
            id=sub_part.get("id", str(uuid4())),
            name=sub_part.get("name", "Unknown"),
            quantity=sub_part.get("quantity", 1.0),
            unit=sub_part.get("unit", "pieces"),
            sub_components=sub_components,
            reference=reference,
            requirements=requirements,
            metadata=metadata,
        )

    async def resolve_bom(
        self,
        okh_manifest: OKHManifest,
        okh_service: Optional[OKHService] = None,
        manifest_path: Optional[str] = None,
    ) -> BillOfMaterials:
        """
        Resolve BOM from OKH manifest, handling both embedded and external BOMs.

        Adaptive approach:
        - If external BOM is specified, try to load it first
        - If external BOM fails or has unresolvable references, fall back to embedded parts
        - If no BOM is found, return empty BOM

        Args:
            okh_manifest: OKH manifest to resolve BOM from
            okh_service: OKHService instance (optional, uses self.okh_service if not provided)
            manifest_path: Path to OKH manifest file (for resolving relative BOM paths)

        Returns:
            BillOfMaterials object (may be empty if no BOM found)
        """
        bom_type = self._detect_bom_type(okh_manifest)

        if bom_type == "embedded":
            return await self._load_embedded_bom(okh_manifest)
        elif bom_type == "external":
            # Try external BOM first
            service = okh_service or self.okh_service
            # Use provided manifest_path, or try to get from service if available
            if not manifest_path and service and hasattr(service, "get_manifest_path"):
                try:
                    manifest_path = await service.get_manifest_path(okh_manifest.id)
                except Exception:
                    pass  # Continue without manifest_path

            try:
                external_bom = await self._load_external_bom(
                    okh_manifest, service, manifest_path
                )
                # Check if external BOM has any components
                if external_bom and external_bom.components:
                    # Always include embedded parts if available (they're part of the OKH manifest)
                    # This ensures we match all components, even if external BOM has unresolved references
                    if okh_manifest.parts or okh_manifest.sub_parts:
                        logger.info(
                            f"External BOM loaded with {len(external_bom.components)} components. "
                            f"Including embedded parts as well for comprehensive matching.",
                            extra={
                                "okh_id": str(okh_manifest.id),
                                "external_components": len(external_bom.components),
                            },
                        )
                        embedded_bom = await self._load_embedded_bom(okh_manifest)
                        # Merge: combine external BOM and embedded parts
                        # Use a set to track component IDs to avoid duplicates
                        seen_ids = set()
                        merged_components = []

                        # Add embedded parts first (they're directly from the OKH manifest)
                        for emb_comp in embedded_bom.components:
                            if emb_comp.id not in seen_ids:
                                merged_components.append(emb_comp)
                                seen_ids.add(emb_comp.id)

                        # Add external BOM components (may have references to other OKHs)
                        for ext_comp in external_bom.components:
                            if ext_comp.id not in seen_ids:
                                merged_components.append(ext_comp)
                                seen_ids.add(ext_comp.id)

                        logger.info(
                            f"Merged BOM: {len(embedded_bom.components)} embedded + "
                            f"{len(external_bom.components)} external = {len(merged_components)} total components",
                            extra={
                                "okh_id": str(okh_manifest.id),
                                "embedded_count": len(embedded_bom.components),
                                "external_count": len(external_bom.components),
                                "total_count": len(merged_components),
                            },
                        )

                        return BillOfMaterials(
                            name=external_bom.name,
                            components=merged_components,
                            metadata={
                                **(external_bom.metadata or {}),
                                "source": "external_and_embedded",
                                "external_component_count": len(
                                    external_bom.components
                                ),
                                "embedded_component_count": len(
                                    embedded_bom.components
                                ),
                            },
                        )
                    else:
                        logger.info(
                            f"Successfully loaded external BOM with {len(external_bom.components)} components",
                            extra={
                                "okh_id": str(okh_manifest.id),
                                "bom_name": external_bom.name,
                            },
                        )
                        return external_bom
                else:
                    logger.warning(
                        "External BOM loaded but has no components, falling back to embedded parts",
                        extra={"okh_id": str(okh_manifest.id)},
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to load external BOM, falling back to embedded parts: {e}",
                    extra={
                        "okh_id": str(okh_manifest.id),
                        "error_type": type(e).__name__,
                    },
                )

            # Fallback to embedded parts if external BOM failed or is empty
            if okh_manifest.parts or okh_manifest.sub_parts:
                logger.info(
                    "Using embedded parts as fallback for BOM resolution",
                    extra={"okh_id": str(okh_manifest.id)},
                )
                return await self._load_embedded_bom(okh_manifest)
            else:
                logger.warning(
                    "External BOM failed and no embedded parts available, returning empty BOM",
                    extra={"okh_id": str(okh_manifest.id)},
                )
                return BillOfMaterials(
                    name=okh_manifest.title or "Unknown", components=[]
                )
        else:
            # No BOM found - create empty BOM
            logger.debug(
                "No BOM found in manifest (neither external nor embedded)",
                extra={"okh_id": str(okh_manifest.id)},
            )
            return BillOfMaterials(name=okh_manifest.title or "Unknown", components=[])

    async def resolve_component_reference(
        self,
        reference: Optional[Dict[str, str]],
        okh_service: Optional[OKHService] = None,
        base_path: Optional[str] = None,
    ) -> Optional[OKHManifest]:
        """
        Resolve component reference to external OKH manifest.

        Supports multiple reference formats:
        - By ID: {"okh_id": "uuid-string"} → uses OKHService.get(UUID)
        - By path: {"path": "path/to/manifest.okh.json"} → loads from filesystem/storage
        - By URL: {"url": "https://..."} → loads from URL (future enhancement)

        Args:
            reference: Component reference dict (can be None)
            okh_service: OKHService instance for loading manifests (optional)
            base_path: Base path for resolving relative paths (optional)

        Returns:
            OKHManifest if found, None otherwise
        """
        if not reference:
            return None

        if not isinstance(reference, dict):
            logger.warning(f"Invalid component reference format: {type(reference)}")
            return None

        # Use provided okh_service or self.okh_service
        service = okh_service or self.okh_service
        if not service:
            logger.warning("No OKHService available for resolving component reference")
            return None

        # Try to resolve by ID first
        if "okh_id" in reference:
            okh_id_str = reference["okh_id"]
            try:
                okh_id = UUID(okh_id_str)
                manifest = await service.get(okh_id)
                if manifest:
                    logger.debug(f"Resolved component reference by ID: {okh_id}")
                    return manifest
                else:
                    logger.warning(f"OKH manifest not found for ID: {okh_id}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid OKH ID format: {okh_id_str}, error: {e}")

        # Try to resolve by path
        if "path" in reference:
            path = reference["path"]
            try:
                # Resolve path relative to base_path if provided
                if base_path and not os.path.isabs(path):
                    resolved_path = self._resolve_bom_path(path, base_path)
                else:
                    resolved_path = path

                # Try to load manifest from path
                manifest = await self._load_manifest_from_path(resolved_path, service)
                if manifest:
                    logger.debug(
                        f"Resolved component reference by path: {resolved_path}"
                    )
                    return manifest
                else:
                    logger.warning(f"OKH manifest not found at path: {resolved_path}")
            except Exception as e:
                logger.warning(f"Error loading OKH manifest from path {path}: {e}")

        # Try to resolve by URL (future enhancement)
        if "url" in reference:
            logger.warning("URL-based component references not yet implemented")
            return None

        # If we get here, the reference format is not supported
        logger.warning(
            f"Unsupported component reference format: {list(reference.keys())}"
        )
        return None

    async def _load_manifest_from_path(
        self, file_path: str, okh_service: Optional[OKHService] = None
    ) -> Optional[OKHManifest]:
        """
        Load OKH manifest from file path.

        Args:
            file_path: Path to OKH manifest file
            okh_service: OKHService instance (optional, for storage-based loading)

        Returns:
            OKHManifest if found, None otherwise
        """
        # Try filesystem first
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    data = json.loads(content)
                    return OKHManifest.from_dict(data)
            except Exception as e:
                logger.warning(
                    f"Failed to load OKH manifest from filesystem {file_path}: {e}"
                )

        # If OKHService provided and has load_file method, try that
        if okh_service and hasattr(okh_service, "load_file"):
            try:
                content = await okh_service.load_file(file_path)
                data = json.loads(content)
                return OKHManifest.from_dict(data)
            except Exception as e:
                logger.warning(
                    f"Failed to load OKH manifest via OKHService {file_path}: {e}"
                )

        return None

    async def explode_bom(
        self,
        bom: BillOfMaterials,
        okh_service: Optional[OKHService] = None,
        max_depth: Optional[int] = None,
        current_depth: int = 0,
        parent_id: Optional[str] = None,
        path: Optional[List[str]] = None,
    ) -> List[ComponentMatch]:
        """
        Recursively explode BOM into flat list with depth tracking.

        Algorithm:
        1. For each component in BOM:
           a. Create ComponentMatch with current depth and path
           b. If component has reference to external OKH:
              - Load OKH manifest
              - If OKH has BOM, recursively explode it
           c. If component has sub-components:
              - Recursively explode sub-components (depth + 1)
           d. Add ComponentMatch to result list
        2. Return flat list of ComponentMatches

        Args:
            bom: BillOfMaterials to explode
            okh_service: OKHService instance for resolving references (optional)
            max_depth: Maximum nesting depth (default: 5)
            current_depth: Current depth in recursion (default: 0)
            parent_id: ID of parent component (None for root)
            path: Path from root component (e.g., ['Device', 'Housing'])

        Returns:
            List of ComponentMatch objects

        Raises:
            ValueError: If max_depth is exceeded
        """
        # Use configured default if max_depth not provided
        if max_depth is None:
            max_depth = MAX_DEPTH

        if path is None:
            path = []

        if current_depth >= max_depth:
            raise ValueError(f"Max depth {max_depth} exceeded at depth {current_depth}")

        component_matches = []

        # Use provided okh_service or self.okh_service
        service = okh_service or self.okh_service

        for component in bom.components:
            # Build component path
            component_path = path + [component.name]

            # Create ComponentMatch
            component_match = ComponentMatch(
                component=component,
                depth=current_depth,
                parent_component_id=parent_id,
                path=component_path,
            )

            # Resolve external OKH reference if present (graceful failure)
            if component.reference and service:
                try:
                    okh_manifest = await self.resolve_component_reference(
                        component.reference, service
                    )
                    if not okh_manifest:
                        # Reference couldn't be resolved - log warning but continue
                        logger.warning(
                            f"Component '{component.name}' has unresolved reference, "
                            f"will use component data directly for matching",
                            extra={
                                "component_id": component.id,
                                "component_name": component.name,
                                "reference": component.reference,
                                "depth": current_depth,
                                "path": " > ".join(component_path),
                            },
                        )
                        # Mark component match as having unresolved reference
                        component_match.has_unresolved_reference = True
                        component_match.unresolved_reference = component.reference
                    if okh_manifest:
                        component_match.okh_manifest = okh_manifest

                        # If referenced OKH has BOM (embedded or external), explode it
                        # Check depth before recursing
                        if (current_depth + 1) < max_depth:
                            try:
                                nested_bom = await self.resolve_bom(
                                    okh_manifest, service
                                )
                                if nested_bom.components:
                                    nested_matches = await self.explode_bom(
                                        nested_bom,
                                        service,
                                        max_depth,
                                        current_depth + 1,
                                        component.id,
                                        component_path,
                                    )
                                    component_matches.extend(nested_matches)
                            except Exception as e:
                                logger.warning(
                                    f"Failed to explode nested BOM for component '{component.name}': {e}",
                                    extra={
                                        "component_id": component.id,
                                        "component_name": component.name,
                                        "depth": current_depth,
                                        "error_type": type(e).__name__,
                                    },
                                )
                except Exception as e:
                    logger.warning(
                        f"Error resolving component reference for '{component.name}': {e}. "
                        f"Continuing with component data directly.",
                        extra={
                            "component_id": component.id,
                            "component_name": component.name,
                            "reference": component.reference,
                            "depth": current_depth,
                            "error_type": type(e).__name__,
                            "path": " > ".join(component_path),
                        },
                    )
                    # Continue processing - component match will use component data directly

            # Explode sub-components if present (check depth before recursing)
            if component.sub_components and (current_depth + 1) < max_depth:
                for sub_component in component.sub_components:
                    # Create temporary BOM for sub-components
                    sub_bom = BillOfMaterials(
                        name=f"{component.name} Sub-components",
                        components=[sub_component],
                    )
                    sub_matches = await self.explode_bom(
                        sub_bom,
                        service,
                        max_depth,
                        current_depth + 1,
                        component.id,
                        component_path,
                    )
                    component_matches.extend(sub_matches)

            component_matches.append(component_match)

        return component_matches
