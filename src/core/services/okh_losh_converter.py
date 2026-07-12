"""
OKH-LOSH v2.4 TOML Converter Service for Open Hardware Manager (OHM).

Converts OKH-LOSH v2.4 manifests — the TOML format defined by
github.com/iop-alliance/OpenKnowHow, authored with kebab-case field names —
into OHM's canonical OKHManifest.

The OKH canonical data model is always the source of truth. This converter
is one direction only (TOML -> OKH): nothing in OHM needs to export a
manifest back to OKH-LOSH TOML, unlike the bidirectional MSF datasheet
converter.

Usage:
    converter = OkhLoshConverter()
    manifest = converter.okh_losh_to_okh("my-project.okh.toml")
"""

import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..models.okh import DocumentationType, OKHManifest
from ..utils.logging import get_logger

logger = get_logger(__name__)


class OkhLoshConversionError(Exception):
    """Raised when OKH-LOSH TOML conversion fails."""

    pass


class OkhLoshConverter:
    """Converts OKH-LOSH v2.4 TOML manifests to canonical OKHManifest.

    OKH-LOSH v2.4 (https://github.com/iop-alliance/OpenKnowHow) uses
    kebab-case field names and a handful of shapes (repeatable [[image]]
    tables, a top-level [outer-dimensions] table, a top-level mass) that
    have no equivalent in OHM's canonical model. Fields with no OHM
    equivalent are preserved under ``metadata.*`` rather than dropped.
    """

    # Fields with an identical name and value shape on both sides.
    _PASSTHROUGH = [
        "repo",
        "license",
        "function",
        "version",
        "licensor",
        "organization",
        "attestation",
        "bom",
        "readme",
    ]

    # kebab-case -> snake_case renames (identical value shape both sides).
    _DIRECT_RENAMES = {
        "documentation-language": "documentation_language",
        "technology-readiness-level": "technology_readiness_level",
        "documentation-readiness-level": "documentation_readiness_level",
        "cpc-patent-class": "cpc_patent_class",
        "contribution-guide": "contribution_guide",
    }

    # OKH-LOSH field -> (OHM DocumentRef list field, DocumentationType)
    _DOC_REF_FIELDS = {
        "manufacturing-instructions": (
            "making_instructions",
            DocumentationType.MAKING_INSTRUCTIONS,
        ),
        "user-manual": (
            "operating_instructions",
            DocumentationType.OPERATING_INSTRUCTIONS,
        ),
        "publication": ("publications", DocumentationType.PUBLICATIONS),
        "source": ("design_files", DocumentationType.DESIGN_FILES),
    }

    def okh_losh_to_okh(self, toml_path: Union[str, Path]) -> OKHManifest:
        """Parse an OKH-LOSH v2.4 TOML file and return a canonical OKHManifest.

        Args:
            toml_path: Path to the OKH-LOSH TOML file.

        Returns:
            An OKHManifest populated from the TOML fields.

        Raises:
            OkhLoshConversionError: If the file is missing, not valid TOML,
                or cannot be built into an OKHManifest.
        """
        toml_path = Path(toml_path)
        if not toml_path.exists():
            raise OkhLoshConversionError(f"File not found: {toml_path}")

        try:
            with open(toml_path, "rb") as f:
                data = tomllib.load(f)
        except tomllib.TOMLDecodeError as exc:
            raise OkhLoshConversionError(f"Invalid TOML in {toml_path}: {exc}") from exc

        normalized: Dict[str, Any] = {"title": data.get("name", toml_path.stem)}
        metadata: Dict[str, Any] = {}

        if "okhv" in data:
            # Pass through literally; OHM does not validate/enforce this field.
            normalized["okhv"] = data["okhv"]

        for field in self._PASSTHROUGH:
            if field in data:
                normalized[field] = data[field]

        for src, dest in self._DIRECT_RENAMES.items():
            if src in data:
                normalized[dest] = data[src]

        if "tsdc" in data:
            tsdc = data["tsdc"]
            normalized["tsdc"] = tsdc if isinstance(tsdc, list) else [tsdc]

        if "standard-compliance" in data:
            sc = data["standard-compliance"]
            normalized["standards_used"] = sc if isinstance(sc, list) else [sc]

        for src, (dest, doc_type) in self._DOC_REF_FIELDS.items():
            if src in data:
                values = data[src]
                values = values if isinstance(values, list) else [values]
                label = dest.replace("_", " ").title()
                normalized[dest] = [
                    {"title": f"{label} {i + 1}", "path": v, "type": doc_type.value}
                    for i, v in enumerate(values)
                ]

        if "software" in data:
            # Sub-field is kebab-case (`installation-guide`) in the source;
            # a raw pass-through would silently lose it under OHM's
            # snake_case `installation_guide`.
            normalized["software"] = [
                {
                    "release": sw.get("release", ""),
                    "installation_guide": sw.get("installation-guide"),
                }
                for sw in data["software"]
            ]

        if "outer-dimensions" in data:
            # Untyped dict on both sides; preserve keys (width/depth/height) as-is.
            normalized["manufacturing_specs"] = {
                "outer_dimensions": data["outer-dimensions"]
            }

        if "image" in data:
            images = data["image"]
            images = images if isinstance(images, list) else [{"location": images}]
            primary = self._pick_primary_image(images)
            if primary:
                normalized["image"] = primary
            metadata["images"] = images

        if "mass" in data:
            # No top-level equivalent in OHM (only nested under PartSpec.mass).
            metadata["mass"] = data["mass"]

        if "release" in data:
            # OKH-LOSH's top-level release URL is a different concept from
            # OHM's Software.release (a per-software-dependency release URL).
            metadata["release"] = data["release"]

        if metadata:
            normalized["metadata"] = metadata

        try:
            manifest = OKHManifest.from_dict(normalized)
        except Exception as exc:
            raise OkhLoshConversionError(
                f"Failed to build OKH manifest from {toml_path}: {exc}"
            ) from exc

        logger.info(
            f"OKH-LOSH manifest parsed: {manifest.title} (from {toml_path.name})"
        )
        return manifest

    @staticmethod
    def _pick_primary_image(images: List[Dict[str, Any]]) -> Optional[str]:
        """Pick a single representative image location from an OKH-LOSH [[image]] array.

        Prefers the image tagged with the `photo-thing-main` slot; falls back
        to the first image with a location. The full array (with slots/tags/
        depicts) is preserved separately in `metadata.images`.
        """
        for img in images:
            if isinstance(img, dict) and "photo-thing-main" in (img.get("slots") or []):
                return img.get("location")
        for img in images:
            if isinstance(img, dict) and img.get("location"):
                return img["location"]
        return None
