"""
Canonical File Type Taxonomy.

Single source of truth for file extension → technical type, OKH role, and UI render tier.
"""

from __future__ import annotations

import logging
import mimetypes
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, FrozenSet, List, Optional, Set

import yaml

from src.core.utils.file_path_display import normalize_display_path

logger = logging.getLogger(__name__)

DEFAULT_FILE_TYPES_PATH: Path = (
    Path(__file__).resolve().parent.parent.parent
    / "config"
    / "taxonomy"
    / "file_types.yaml"
)

# Directory names that indicate manufacturing context for grey-zone extensions.
_MANUFACTURING_CONTEXT_DIRS = frozenset(
    {
        "cam",
        "output",
        "export",
        "exports",
        "gcode",
        "gcodes",
        "stl",
        "stls",
        "meshes",
        "mesh",
        "print",
        "prints",
        "fabrication",
        "fab",
        "laser",
        "cut",
        "cuts",
        "manufacturing",
        "mfg",
        "production",
        "sliced",
        "slicer",
    }
)

_DESIGN_CONTEXT_DIRS = frozenset(
    {
        "design",
        "designs",
        "cad",
        "source",
        "sources",
        "src",
        "model",
        "models",
        "parametric",
        "openscad",
        "fusion",
        "freecad",
    }
)


@dataclass(frozen=True)
class FileTypeDefinition:
    """Definition of a single canonical file type."""

    canonical_id: str
    display_name: str
    extensions: FrozenSet[str] = field(default_factory=frozenset)
    mime_types: FrozenSet[str] = field(default_factory=frozenset)
    parent: Optional[str] = None
    okh_role: str = "documentation"
    render_tier: str = "download_only"


@dataclass(frozen=True)
class FileClassification:
    """Result of classifying a file path."""

    file_type: str
    display_name: str
    okh_role: str
    render_tier: str
    mime_type: str


# Minimal bootstrap when YAML is unavailable.
FILE_TYPE_DEFINITIONS: List[FileTypeDefinition] = [
    FileTypeDefinition(
        canonical_id="unknown",
        display_name="Unknown",
        render_tier="download_only",
    ),
]


def load_from_yaml(path: Path) -> List[FileTypeDefinition]:
    """Load file type definitions from YAML."""
    if not path.exists():
        raise FileNotFoundError(f"File types YAML not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("File types YAML root must be a mapping")

    section: Any = data.get("file_types")
    if not section or not isinstance(section, dict):
        raise ValueError(
            "File types YAML must contain a non-empty 'file_types' mapping"
        )

    definitions: List[FileTypeDefinition] = []
    for canonical_id, entry in section.items():
        if not isinstance(entry, dict):
            raise ValueError(f"File type '{canonical_id}': expected mapping")

        display_name = entry.get("display_name")
        if not display_name:
            raise ValueError(f"File type '{canonical_id}': missing display_name")

        raw_ext = entry.get("extensions", [])
        raw_mime = entry.get("mime_types", [])
        if not isinstance(raw_ext, list):
            raise ValueError(f"File type '{canonical_id}': extensions must be a list")
        if not isinstance(raw_mime, list):
            raise ValueError(f"File type '{canonical_id}': mime_types must be a list")

        extensions = frozenset(
            e if str(e).startswith(".") else f".{e}" for e in raw_ext if e
        )
        mime_types = frozenset(str(m) for m in raw_mime if m)

        definitions.append(
            FileTypeDefinition(
                canonical_id=str(canonical_id),
                display_name=str(display_name),
                extensions=extensions,
                mime_types=mime_types,
                parent=str(entry["parent"]) if entry.get("parent") else None,
                okh_role=str(entry.get("okh_role", "documentation")),
                render_tier=str(entry.get("render_tier", "download_only")),
            )
        )

    logger.info(
        "Loaded %d file type definitions from %s (version %s)",
        len(definitions),
        path,
        data.get("version", "unknown"),
    )
    return definitions


def validate_definitions(definitions: List[FileTypeDefinition]) -> List[str]:
    """Validate file type definitions."""
    errors: List[str] = []
    id_set: Set[str] = set()
    ext_owner: dict[str, str] = {}

    for defn in definitions:
        cid = defn.canonical_id
        if cid in id_set:
            errors.append(f"Duplicate canonical_id: '{cid}'")
        id_set.add(cid)

        if cid != cid.lower() or not re.match(r"^[a-z0-9][a-z0-9_]*$", cid):
            errors.append(f"canonical_id '{cid}' is not lowercase snake_case")

        if not defn.display_name.strip():
            errors.append(f"File type '{cid}': display_name is empty")

        valid_roles = {
            "design",
            "manufacturing",
            "grey_zone",
            "documentation",
            "software",
        }
        if defn.okh_role not in valid_roles:
            errors.append(f"File type '{cid}': invalid okh_role '{defn.okh_role}'")

        valid_tiers = {"native_inline", "text_viewer", "wasm_3d", "download_only"}
        if defn.render_tier not in valid_tiers:
            errors.append(
                f"File type '{cid}': invalid render_tier '{defn.render_tier}'"
            )

    for defn in definitions:
        if defn.parent and defn.parent not in id_set:
            errors.append(
                f"File type '{defn.canonical_id}': parent '{defn.parent}' does not exist"
            )

    for defn in definitions:
        for ext in defn.extensions:
            key = ext.lower()
            if key in ext_owner and ext_owner[key] != defn.canonical_id:
                errors.append(
                    f"Extension collision: '{ext}' maps to both "
                    f"'{ext_owner[key]}' and '{defn.canonical_id}'"
                )
            else:
                ext_owner[key] = defn.canonical_id

    return errors


class FileTypeTaxonomy:
    """Canonical file type taxonomy."""

    def __init__(self, definitions: Optional[List[FileTypeDefinition]] = None) -> None:
        if definitions is None:
            definitions = list(FILE_TYPE_DEFINITIONS)

        self._definitions: dict[str, FileTypeDefinition] = {}
        self._extension_map: dict[str, str] = {}
        self._mime_map: dict[str, str] = {}
        self._source_path: Optional[Path] = None

        for defn in definitions:
            self._definitions[defn.canonical_id] = defn
            for ext in defn.extensions:
                self._extension_map[ext.lower()] = defn.canonical_id
            for mime in defn.mime_types:
                self._mime_map[mime.lower()] = defn.canonical_id

        if not self._definitions.get("unknown"):
            self._definitions["unknown"] = FileTypeDefinition(
                canonical_id="unknown",
                display_name="Unknown",
                render_tier="download_only",
            )

    def get_definition(self, canonical_id: str) -> Optional[FileTypeDefinition]:
        return self._definitions.get(canonical_id)

    def get_all_canonical_ids(self) -> Set[str]:
        return set(self._definitions.keys())

    def _resolve_grey_zone_role(self, display_path: str) -> str:
        """Resolve grey_zone okh_role from directory context."""
        parts = {p.lower() for p in display_path.split("/")[:-1]}
        if parts & _MANUFACTURING_CONTEXT_DIRS:
            return "manufacturing"
        if parts & _DESIGN_CONTEXT_DIRS:
            return "design"
        return "manufacturing"

    def guess_mime_type(self, path: str, content: Optional[bytes] = None) -> str:
        """Guess MIME type from path and optional content sniffing."""
        display_path = normalize_display_path(path)
        ext = Path(display_path).suffix.lower()
        if ext and ext in self._extension_map:
            defn = self._definitions.get(self._extension_map[ext])
            if defn and defn.mime_types:
                return sorted(defn.mime_types)[0]

        media_type, _ = mimetypes.guess_type(display_path)
        if media_type:
            return media_type
        if content and content[:5] == b"%PDF-":
            return "application/pdf"
        return "application/octet-stream"

    def classify(
        self,
        path: str,
        *,
        mime_type: Optional[str] = None,
        content: Optional[bytes] = None,
    ) -> FileClassification:
        """Classify a file path into technical type, OKH role, and render tier."""
        display_path = normalize_display_path(path)
        ext = Path(display_path).suffix.lower()

        canonical_id = "unknown"
        if ext and ext in self._extension_map:
            canonical_id = self._extension_map[ext]
        elif mime_type:
            canonical_id = self._mime_map.get(
                mime_type.lower().split(";")[0].strip(), "unknown"
            )

        defn = self._definitions.get(canonical_id) or self._definitions["unknown"]
        resolved_mime = mime_type or self.guess_mime_type(path, content)

        okh_role = defn.okh_role
        if okh_role == "grey_zone":
            okh_role = self._resolve_grey_zone_role(display_path)

        return FileClassification(
            file_type=defn.canonical_id,
            display_name=defn.display_name,
            okh_role=okh_role,
            render_tier=defn.render_tier,
            mime_type=resolved_mime,
        )


def _load_default_taxonomy() -> FileTypeTaxonomy:
    try:
        if DEFAULT_FILE_TYPES_PATH.exists():
            definitions = load_from_yaml(DEFAULT_FILE_TYPES_PATH)
            errors = validate_definitions(definitions)
            if errors:
                logger.warning(
                    "File type YAML validation errors, using bootstrap: %s", errors
                )
                return FileTypeTaxonomy()
            taxonomy = FileTypeTaxonomy(definitions)
            taxonomy._source_path = DEFAULT_FILE_TYPES_PATH
            return taxonomy
    except Exception as exc:
        logger.warning("Failed to load file types YAML, using bootstrap: %s", exc)
    return FileTypeTaxonomy()


file_type_taxonomy = _load_default_taxonomy()
