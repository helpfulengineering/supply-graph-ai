"""
Canonical Process Taxonomy for Manufacturing Processes.

This module provides a single source of truth for manufacturing process
identification. It replaces the 6+ scattered normalization/mapping functions
that previously existed across the codebase, each with incomplete dictionaries.

Design principles:
- Canonical IDs are lowercase snake_case strings (internal identifiers)
- A many-to-one alias table maps every known form (TSDC codes, Wikipedia URIs,
  plain English names, abbreviations, Wikipedia slugs) to canonical IDs
- Hierarchy supports parent-child relationships (e.g., 3d_printing_fdm -> 3d_printing)
- Unknown processes return None rather than raising, allowing NLP fallback
- Instantiated as a module-level singleton (pure data, no side effects)

Usage:
    from src.core.taxonomy import taxonomy

    canonical_id = taxonomy.normalize("3DP")           # -> "3d_printing"
    canonical_id = taxonomy.normalize("CNC")           # -> "cnc_machining"
    canonical_id = taxonomy.normalize("https://en.wikipedia.org/wiki/Laser_cutting")  # -> "laser_cutting"

    is_known = taxonomy.is_valid("Fused filament fabrication")  # -> True
    display = taxonomy.get_display_name("3d_printing")          # -> "3D Printing"
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default path for the YAML taxonomy file
# ---------------------------------------------------------------------------
# Resolved relative to this file: src/core/taxonomy/ -> src/config/taxonomy/
DEFAULT_TAXONOMY_PATH: Path = (
    Path(__file__).resolve().parent.parent.parent
    / "config"
    / "taxonomy"
    / "processes.yaml"
)


@dataclass(frozen=True)
class ProcessDefinition:
    """Definition of a single canonical manufacturing process."""

    canonical_id: str
    display_name: str
    tsdc_code: Optional[str] = None
    parent: Optional[str] = None
    aliases: FrozenSet[str] = field(default_factory=frozenset)


# ---------------------------------------------------------------------------
# Canonical Process Definitions
# ---------------------------------------------------------------------------
# Each definition includes:
#   - canonical_id: the internal identifier (lowercase snake_case)
#   - display_name: human-readable label
#   - tsdc_code: TSDC code from DIN SPEC 3105 (if applicable)
#   - parent: canonical_id of parent process (for hierarchy)
#   - aliases: all known alternative names, abbreviations, Wikipedia slugs,
#     and URI fragments that should resolve to this canonical ID
#
# IMPORTANT: aliases are matched CASE-INSENSITIVELY after normalization.
# Do NOT include Wikipedia full URLs here; they are handled by URI extraction.
# Include only the slug portion (the part after /wiki/).
# ---------------------------------------------------------------------------

PROCESS_DEFINITIONS: List[ProcessDefinition] = [
    # -----------------------------------------------------------------------
    # Additive Manufacturing (TSDC: 3DP)
    # -----------------------------------------------------------------------
    ProcessDefinition(
        canonical_id="3d_printing",
        display_name="3D Printing",
        tsdc_code="3DP",
        parent=None,
        aliases=frozenset(
            {
                "3dp",
                "3d printing",
                "3d print",
                "3d_printing",
                "additive manufacturing",
                "am",
                "printing",
                "print",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="3d_printing_fdm",
        display_name="FDM 3D Printing",
        tsdc_code=None,
        parent="3d_printing",
        aliases=frozenset(
            {
                "fdm",
                "fdm printing",
                "fused deposition modeling",
                "fused deposition modelling",
                "fused filament fabrication",
                "fused_filament_fabrication",
                "fff",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="3d_printing_sla",
        display_name="SLA 3D Printing",
        tsdc_code=None,
        parent="3d_printing",
        aliases=frozenset(
            {
                "sla",
                "sla printing",
                "stereolithography",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="3d_printing_sls",
        display_name="SLS 3D Printing",
        tsdc_code=None,
        parent="3d_printing",
        aliases=frozenset(
            {
                "sls",
                "sls printing",
                "selective laser sintering",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="3d_printing_dlp",
        display_name="DLP 3D Printing",
        tsdc_code=None,
        parent="3d_printing",
        aliases=frozenset(
            {
                "dlp",
                "dlp printing",
                "digital light processing",
            }
        ),
    ),
    # -----------------------------------------------------------------------
    # Subtractive Manufacturing (TSDC: CNC)
    # -----------------------------------------------------------------------
    ProcessDefinition(
        canonical_id="cnc_machining",
        display_name="CNC Machining",
        tsdc_code="CNC",
        parent=None,
        aliases=frozenset(
            {
                "cnc",
                "cnc machining",
                "cnc_machining",
                "computer numerical control",
                "subtractive manufacturing",
                "machining",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="cnc_milling",
        display_name="CNC Milling",
        tsdc_code=None,
        parent="cnc_machining",
        aliases=frozenset(
            {
                "cnc milling",
                "cnc_milling",
                "cnc mill",
                "cnc_mill",
                "milling",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="cnc_turning",
        display_name="CNC Turning",
        tsdc_code=None,
        parent="cnc_machining",
        aliases=frozenset(
            {
                "cnc turning",
                "cnc_turning",
                "cnc lathe",
                "cnc_lathe",
                "turning",
            }
        ),
    ),
    # -----------------------------------------------------------------------
    # Laser Processes (TSDC: LAS)
    # -----------------------------------------------------------------------
    ProcessDefinition(
        canonical_id="laser_cutting",
        display_name="Laser Cutting",
        tsdc_code="LAS",
        parent=None,
        aliases=frozenset(
            {
                "las",
                "laser",
                "laser cutting",
                "laser_cutting",
                "laser cut",
            }
        ),
    ),
    # -----------------------------------------------------------------------
    # PCB (TSDC: PCB)
    # -----------------------------------------------------------------------
    ProcessDefinition(
        canonical_id="pcb_fabrication",
        display_name="PCB Fabrication",
        tsdc_code="PCB",
        parent=None,
        aliases=frozenset(
            {
                "pcb",
                "pcb fabrication",
                "pcb_fabrication",
                "printed circuit board",
                "printed_circuit_board",
                "circuit board",
            }
        ),
    ),
    # -----------------------------------------------------------------------
    # Assembly (TSDC: ASM)
    # -----------------------------------------------------------------------
    ProcessDefinition(
        canonical_id="assembly",
        display_name="Assembly",
        tsdc_code="ASM",
        parent=None,
        aliases=frozenset(
            {
                "asm",
                "assembly",
                "assembly line",
                "assembly_line",
                "assemble",
                "assembling",
                "component assembly",
                "attach",
                "attaching",
                "install",
                "installing",
                "mount",
                "mounting",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="mechanical_assembly",
        display_name="Mechanical Assembly",
        tsdc_code="MEC",
        parent="assembly",
        aliases=frozenset(
            {
                "mec",
                "mechanical assembly",
                "mechanical_assembly",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="electronics_assembly",
        display_name="Electronics Assembly",
        tsdc_code=None,
        parent="assembly",
        aliases=frozenset(
            {
                "electronics assembly",
                "electronics_assembly",
                "electronics manufacturing",
                "electronics_manufacturing",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="pcb_assembly",
        display_name="PCB Assembly",
        tsdc_code=None,
        parent="assembly",
        aliases=frozenset(
            {
                "pcb assembly",
                "pcb_assembly",
                "clean room assembly",
                "clean_room_assembly",
            }
        ),
    ),
    # -----------------------------------------------------------------------
    # Welding (TSDC: WEL)
    # -----------------------------------------------------------------------
    ProcessDefinition(
        canonical_id="welding",
        display_name="Welding",
        tsdc_code="WEL",
        parent=None,
        aliases=frozenset(
            {
                "wel",
                "welding",
                "weld",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="tig_welding",
        display_name="TIG Welding",
        tsdc_code=None,
        parent="welding",
        aliases=frozenset(
            {
                "tig welding",
                "tig_welding",
                "tig",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="mig_welding",
        display_name="MIG Welding",
        tsdc_code=None,
        parent="welding",
        aliases=frozenset(
            {
                "mig welding",
                "mig_welding",
                "mig",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="arc_welding",
        display_name="Arc Welding",
        tsdc_code=None,
        parent="welding",
        aliases=frozenset(
            {
                "arc welding",
                "arc_welding",
            }
        ),
    ),
    # -----------------------------------------------------------------------
    # Sheet Metal
    # -----------------------------------------------------------------------
    ProcessDefinition(
        canonical_id="sheet_metal_forming",
        display_name="Sheet Metal Forming",
        tsdc_code="SHEET",
        parent=None,
        aliases=frozenset(
            {
                "sheet",
                "sheet metal",
                "sheet metal forming",
                "sheet_metal_forming",
                "sheet_metal",
            }
        ),
    ),
    # -----------------------------------------------------------------------
    # Other Manufacturing Processes
    # -----------------------------------------------------------------------
    ProcessDefinition(
        canonical_id="injection_molding",
        display_name="Injection Molding",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "injection molding",
                "injection_molding",
                "injection moulding",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="water_jet_cutting",
        display_name="Water Jet Cutting",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "water jet cutting",
                "water_jet_cutting",
                "waterjet",
                "water jet",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="casting",
        display_name="Casting",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "casting",
                "cast",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="forging",
        display_name="Forging",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "forging",
                "forge",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="soldering",
        display_name="Soldering",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "soldering",
                "solder",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="drilling",
        display_name="Drilling",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "drilling",
                "drill",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="bending",
        display_name="Bending",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "bending",
                "bend",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="grinding",
        display_name="Grinding",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "grinding",
                "grind",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="polishing",
        display_name="Polishing",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "polishing",
                "polish",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="sanding",
        display_name="Sanding",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "sanding",
                "sand",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="coating",
        display_name="Coating",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "coating",
                "coat",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="anodizing",
        display_name="Anodizing",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "anodizing",
                "anodising",
                "anodize",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="heat_treatment",
        display_name="Heat Treatment",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "heat treatment",
                "heat_treatment",
                "heat treat",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="annealing",
        display_name="Annealing",
        tsdc_code=None,
        parent="heat_treatment",
        aliases=frozenset(
            {
                "annealing",
                "anneal",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="tempering",
        display_name="Tempering",
        tsdc_code=None,
        parent="heat_treatment",
        aliases=frozenset(
            {
                "tempering",
                "temper",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="quenching",
        display_name="Quenching",
        tsdc_code=None,
        parent="heat_treatment",
        aliases=frozenset(
            {
                "quenching",
                "quench",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="plasma_cutting",
        display_name="Plasma Cutting",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "plasma cutting",
                "plasma_cutting",
                "plasma cut",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="surface_finishing",
        display_name="Surface Finishing",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "surface finishing",
                "surface_finishing",
                "surface finish",
                "surface_finish",
                "surface treatment",
                "surface_treatment",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="post_processing",
        display_name="Post-Processing",
        tsdc_code="POST",
        parent=None,
        aliases=frozenset(
            {
                "post",
                "post processing",
                "post_processing",
                "post-processing",
                "postprocessing",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="deburring",
        display_name="Deburring",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "deburring",
                "deburr",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="painting",
        display_name="Painting",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "painting",
                "paint",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="cutting",
        display_name="Cutting",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "cutting",
                "cut",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="sawing",
        display_name="Sawing",
        tsdc_code=None,
        parent="cutting",
        aliases=frozenset(
            {
                "sawing",
                "saw",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="shearing",
        display_name="Shearing",
        tsdc_code=None,
        parent="cutting",
        aliases=frozenset(
            {
                "shearing",
                "shear",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="testing",
        display_name="Testing",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "testing",
                "test equipment",
                "test_equipment",
                "quality control",
                "quality_control",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="packaging",
        display_name="Packaging",
        tsdc_code=None,
        parent=None,
        aliases=frozenset(
            {
                "packaging",
                "packaging and labeling",
                "packaging_and_labeling",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="precision_machining",
        display_name="Precision Machining",
        tsdc_code=None,
        parent="cnc_machining",
        aliases=frozenset(
            {
                "precision machining",
                "precision_machining",
            }
        ),
    ),
    ProcessDefinition(
        canonical_id="electronic_circuitry",
        display_name="Electronic Circuitry",
        tsdc_code="CIR",
        parent=None,
        aliases=frozenset(
            {
                "cir",
                "electronic circuitry",
                "circuitry",
            }
        ),
    ),
]


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


def load_from_yaml(path: Path) -> List[ProcessDefinition]:
    """Load process definitions from a YAML taxonomy file.

    Args:
        path: Path to the YAML file.

    Returns:
        List of ProcessDefinition objects.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the YAML structure is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"Taxonomy YAML file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(
            f"Taxonomy YAML root must be a mapping, got {type(data).__name__}"
        )

    processes_section: Any = data.get("processes")
    if not processes_section or not isinstance(processes_section, dict):
        raise ValueError("Taxonomy YAML must contain a non-empty 'processes' mapping")

    definitions: List[ProcessDefinition] = []
    for canonical_id, entry in processes_section.items():
        if not isinstance(entry, dict):
            raise ValueError(
                f"Process '{canonical_id}': expected a mapping, got {type(entry).__name__}"
            )

        display_name = entry.get("display_name")
        if not display_name:
            raise ValueError(
                f"Process '{canonical_id}': missing required 'display_name'"
            )

        tsdc_code = entry.get("tsdc_code")
        parent = entry.get("parent")
        raw_aliases = entry.get("aliases", [])

        if not isinstance(raw_aliases, list):
            raise ValueError(
                f"Process '{canonical_id}': 'aliases' must be a list, "
                f"got {type(raw_aliases).__name__}"
            )

        aliases = frozenset(str(a) for a in raw_aliases if a)

        definitions.append(
            ProcessDefinition(
                canonical_id=str(canonical_id),
                display_name=str(display_name),
                tsdc_code=str(tsdc_code) if tsdc_code else None,
                parent=str(parent) if parent else None,
                aliases=aliases,
            )
        )

    version = data.get("version", "unknown")
    logger.info(
        "Loaded %d process definitions from %s (version %s)",
        len(definitions),
        path,
        version,
    )
    return definitions


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_definitions(definitions: List[ProcessDefinition]) -> List[str]:
    """Validate a list of process definitions for internal consistency.

    Checks performed:
    - All canonical IDs are unique
    - All canonical IDs are lowercase snake_case
    - All display names are non-empty
    - All parent references point to existing canonical IDs
    - No circular parent hierarchy
    - No alias collisions (two different canonical IDs claiming the same alias)

    Args:
        definitions: List of ProcessDefinition objects to validate.

    Returns:
        List of error message strings. Empty list means valid.
    """
    errors: List[str] = []
    id_set: Set[str] = set()

    # Pass 1: collect IDs, check uniqueness, format, display_name
    for defn in definitions:
        cid = defn.canonical_id

        # Unique IDs
        if cid in id_set:
            errors.append(f"Duplicate canonical_id: '{cid}'")
        id_set.add(cid)

        # Lowercase snake_case
        if cid != cid.lower() or not re.match(r"^[a-z0-9][a-z0-9_]*$", cid):
            errors.append(f"canonical_id '{cid}' is not lowercase snake_case")

        # Display name
        if not defn.display_name or not defn.display_name.strip():
            errors.append(f"Process '{cid}': display_name is empty")

    # Pass 2: parent references and cycles
    for defn in definitions:
        if defn.parent:
            if defn.parent not in id_set:
                errors.append(
                    f"Process '{defn.canonical_id}': parent '{defn.parent}' does not exist"
                )
            else:
                # Check for cycles
                visited: Set[str] = set()
                current: Optional[str] = defn.canonical_id
                defn_map = {d.canonical_id: d for d in definitions}
                while current:
                    if current in visited:
                        errors.append(
                            f"Circular hierarchy detected involving '{defn.canonical_id}'"
                        )
                        break
                    visited.add(current)
                    parent_defn = defn_map.get(current)
                    current = parent_defn.parent if parent_defn else None

    # Pass 3: alias collisions
    alias_owner: Dict[str, str] = {}
    normalize_key = ProcessTaxonomy._normalize_key
    for defn in definitions:
        cid = defn.canonical_id

        # Check the canonical_id itself as an alias
        key = normalize_key(cid)
        if key and key in alias_owner and alias_owner[key] != cid:
            errors.append(
                f"Alias collision: '{key}' maps to both "
                f"'{alias_owner[key]}' and '{cid}'"
            )
        elif key:
            alias_owner[key] = cid

        # Check explicit aliases
        for alias in defn.aliases:
            key = normalize_key(alias)
            if not key:
                continue
            if key in alias_owner and alias_owner[key] != cid:
                errors.append(
                    f"Alias collision: '{key}' (from alias '{alias}') maps to both "
                    f"'{alias_owner[key]}' and '{cid}'"
                )
            else:
                alias_owner[key] = cid

    return errors


class ProcessTaxonomy:
    """
    Canonical manufacturing process taxonomy.

    Provides a single source of truth for normalizing, validating, and
    querying manufacturing process identifiers. Accepts any known form
    (TSDC codes, Wikipedia URIs, plain English, abbreviations) and maps
    to canonical IDs.

    This class is designed to be instantiated once at module load time
    and used as a singleton via the module-level ``taxonomy`` instance.
    """

    def __init__(self, definitions: Optional[List[ProcessDefinition]] = None) -> None:
        if definitions is None:
            definitions = PROCESS_DEFINITIONS

        # Primary storage: canonical_id -> ProcessDefinition
        self._definitions: Dict[str, ProcessDefinition] = {}

        # Lookup: normalized alias -> canonical_id
        self._alias_map: Dict[str, str] = {}

        # Lookup: tsdc_code (uppercase) -> canonical_id
        self._tsdc_map: Dict[str, str] = {}

        # Hierarchy: canonical_id -> set of child canonical_ids
        self._children: Dict[str, Set[str]] = {}

        # Track which file was loaded (None means built-in definitions)
        self._source_path: Optional[Path] = None

        self._build(definitions)

    # ------------------------------------------------------------------
    # Reload
    # ------------------------------------------------------------------

    def reload(self, yaml_path: Optional[Path] = None) -> Dict[str, Any]:
        """Reload the taxonomy from a YAML file.

        This is an atomic operation: if loading or validation fails, the
        current taxonomy state is preserved and an exception is raised.

        Args:
            yaml_path: Path to the YAML file.  Defaults to
                ``DEFAULT_TAXONOMY_PATH`` if not provided.

        Returns:
            Dict with reload summary: ``added``, ``removed``, ``total``,
            ``source``, and ``version``.

        Raises:
            FileNotFoundError: If the YAML file does not exist.
            ValueError: If validation fails.
        """
        path = yaml_path or DEFAULT_TAXONOMY_PATH

        # Load from file
        new_definitions = load_from_yaml(path)

        # Validate before applying
        errors = validate_definitions(new_definitions)
        if errors:
            error_summary = "; ".join(errors[:5])
            if len(errors) > 5:
                error_summary += f" ... and {len(errors) - 5} more"
            raise ValueError(
                f"Taxonomy validation failed ({len(errors)} errors): {error_summary}"
            )

        # Compute diff for logging
        old_ids = set(self._definitions.keys())
        new_ids = {d.canonical_id for d in new_definitions}
        added = new_ids - old_ids
        removed = old_ids - new_ids

        # Atomically rebuild internal state
        self._definitions = {}
        self._alias_map = {}
        self._tsdc_map = {}
        self._children = {}
        self._build(new_definitions)
        self._source_path = path

        # Log changes
        if added:
            logger.info(
                "Taxonomy reload: added processes: %s", ", ".join(sorted(added))
            )
        if removed:
            logger.info(
                "Taxonomy reload: removed processes: %s", ", ".join(sorted(removed))
            )
        logger.info(
            "Taxonomy reloaded from %s: %d processes (%d added, %d removed)",
            path,
            len(new_definitions),
            len(added),
            len(removed),
        )

        # Read version from the YAML metadata
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        version = (
            data.get("version", "unknown") if isinstance(data, dict) else "unknown"
        )

        return {
            "added": sorted(added),
            "removed": sorted(removed),
            "total": len(new_definitions),
            "source": str(path),
            "version": version,
        }

    # ------------------------------------------------------------------
    # Build phase
    # ------------------------------------------------------------------

    def _build(self, definitions: List[ProcessDefinition]) -> None:
        """Build all internal lookup structures from definitions."""
        for defn in definitions:
            cid = defn.canonical_id
            self._definitions[cid] = defn

            # Register canonical ID itself as an alias
            self._register_alias(cid, cid)

            # Register all explicit aliases
            for alias in defn.aliases:
                self._register_alias(alias, cid)

            # Register TSDC code
            if defn.tsdc_code:
                tsdc_upper = defn.tsdc_code.upper()
                self._tsdc_map[tsdc_upper] = cid
                # Also register TSDC code as alias (case-insensitive)
                self._register_alias(defn.tsdc_code, cid)

        # Build children map from parent references
        for defn in definitions:
            if defn.parent:
                if defn.parent not in self._children:
                    self._children[defn.parent] = set()
                self._children[defn.parent].add(defn.canonical_id)

    def _register_alias(self, alias: str, canonical_id: str) -> None:
        """Register a single alias, after key normalization."""
        key = self._normalize_key(alias)
        if not key:
            return
        # First registration wins (prevents accidental overwrite)
        if key not in self._alias_map:
            self._alias_map[key] = canonical_id

    @staticmethod
    def _normalize_key(text: str) -> str:
        """Normalize a string for use as a lookup key.

        - Lowercase
        - Replace underscores and hyphens with spaces
        - Collapse whitespace
        - Strip
        """
        if not text:
            return ""
        key = text.strip().lower()
        key = re.sub(r"[_\-]+", " ", key)
        key = re.sub(r"\s+", " ", key)
        return key.strip()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def normalize(self, input_str: str) -> Optional[str]:
        """Normalize any process identifier to its canonical ID.

        Resolution order:
        1. Exact canonical ID match
        2. Wikipedia URI extraction -> slug -> alias lookup
        3. TSDC code exact match (case-insensitive)
        4. Alias table exact match (after key normalization)
        5. Substring match against alias table keys
        6. Return None (unrecognized)

        Args:
            input_str: Any process identifier (TSDC code, Wikipedia URI,
                        plain name, abbreviation, etc.)

        Returns:
            Canonical ID string, or None if unrecognized.
        """
        if not input_str or not isinstance(input_str, str):
            return None

        text = input_str.strip()
        if not text:
            return None

        # 1. Exact canonical ID match
        if text in self._definitions:
            return text

        # 2. Wikipedia URI extraction
        if "wikipedia.org/wiki/" in text.lower():
            slug = self._extract_wiki_slug(text)
            if slug:
                key = self._normalize_key(slug)
                if key in self._alias_map:
                    return self._alias_map[key]

        # 3. TSDC code exact match
        upper = text.upper().strip()
        if upper in self._tsdc_map:
            return self._tsdc_map[upper]

        # 4. Alias table exact match (after normalization)
        key = self._normalize_key(text)
        if key in self._alias_map:
            return self._alias_map[key]

        # 5. Substring match: check if any alias key is contained in the
        #    input or the input is contained in an alias key
        for alias_key, cid in self._alias_map.items():
            # Skip very short keys to avoid false positives
            if len(alias_key) < 3:
                continue
            if alias_key in key or key in alias_key:
                return cid

        # 6. Unrecognized
        return None

    def is_valid(self, input_str: str) -> bool:
        """Check if a process identifier resolves to any known process.

        Args:
            input_str: Any process identifier.

        Returns:
            True if the input can be normalized to a canonical ID.
        """
        return self.normalize(input_str) is not None

    def get_display_name(self, canonical_id: str) -> str:
        """Get the human-readable display name for a canonical ID.

        Args:
            canonical_id: A canonical process ID.

        Returns:
            Display name string, or the canonical_id itself if unknown.
        """
        defn = self._definitions.get(canonical_id)
        if defn:
            return defn.display_name
        return canonical_id

    def get_tsdc_code(self, canonical_id: str) -> Optional[str]:
        """Get the TSDC code for a canonical ID.

        Walks up the hierarchy to find the nearest TSDC code.

        Args:
            canonical_id: A canonical process ID.

        Returns:
            TSDC code string, or None if no TSDC code is associated.
        """
        current = canonical_id
        visited: Set[str] = set()
        while current and current not in visited:
            visited.add(current)
            defn = self._definitions.get(current)
            if not defn:
                return None
            if defn.tsdc_code:
                return defn.tsdc_code
            current = defn.parent
        return None

    def get_parent(self, canonical_id: str) -> Optional[str]:
        """Get the parent canonical ID.

        Args:
            canonical_id: A canonical process ID.

        Returns:
            Parent canonical ID, or None if this is a root process.
        """
        defn = self._definitions.get(canonical_id)
        if defn:
            return defn.parent
        return None

    def get_children(self, canonical_id: str) -> Set[str]:
        """Get the direct child canonical IDs.

        Args:
            canonical_id: A canonical process ID.

        Returns:
            Set of child canonical IDs (empty set if none or unknown).
        """
        return set(self._children.get(canonical_id, set()))

    def get_ancestors(self, canonical_id: str) -> List[str]:
        """Get all ancestors from immediate parent to root.

        Args:
            canonical_id: A canonical process ID.

        Returns:
            List of ancestor canonical IDs, nearest parent first.
        """
        ancestors: List[str] = []
        current = canonical_id
        visited: Set[str] = set()
        while current and current not in visited:
            visited.add(current)
            defn = self._definitions.get(current)
            if not defn or not defn.parent:
                break
            ancestors.append(defn.parent)
            current = defn.parent
        return ancestors

    def are_related(self, id_a: str, id_b: str) -> bool:
        """Check if two process IDs are related in the hierarchy.

        Two processes are related if:
        - They are the same process
        - One is an ancestor of the other
        - They share a common parent

        Args:
            id_a: First canonical process ID (or any normalizable input).
            id_b: Second canonical process ID (or any normalizable input).

        Returns:
            True if the processes are related.
        """
        # Normalize inputs if needed
        norm_a = self.normalize(id_a) if id_a not in self._definitions else id_a
        norm_b = self.normalize(id_b) if id_b not in self._definitions else id_b

        if norm_a is None or norm_b is None:
            return False

        # Same process
        if norm_a == norm_b:
            return True

        # One is ancestor of the other
        ancestors_a = set(self.get_ancestors(norm_a)) | {norm_a}
        ancestors_b = set(self.get_ancestors(norm_b)) | {norm_b}

        if norm_a in ancestors_b or norm_b in ancestors_a:
            return True

        # Share a common parent (not just root -- direct parent)
        parent_a = self.get_parent(norm_a)
        parent_b = self.get_parent(norm_b)

        if parent_a and parent_b and parent_a == parent_b:
            return True

        return False

    def get_all_canonical_ids(self) -> Set[str]:
        """Return all known canonical process IDs.

        Returns:
            Set of all canonical ID strings.
        """
        return set(self._definitions.keys())

    def get_definition(self, canonical_id: str) -> Optional[ProcessDefinition]:
        """Get the full ProcessDefinition for a canonical ID.

        Args:
            canonical_id: A canonical process ID.

        Returns:
            ProcessDefinition or None.
        """
        return self._definitions.get(canonical_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_wiki_slug(uri: str) -> Optional[str]:
        """Extract the article slug from a Wikipedia URI.

        Examples:
            "https://en.wikipedia.org/wiki/Laser_cutting" -> "Laser_cutting"
            "https://en.wikipedia.org/wiki/Fused_filament_fabrication"
                -> "Fused_filament_fabrication"
        """
        if "/wiki/" not in uri:
            return None
        parts = uri.split("/wiki/")
        if len(parts) > 1 and parts[1]:
            return parts[1].strip().rstrip("/")
        return None


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
# Prefer YAML file if it exists; fall back to built-in PROCESS_DEFINITIONS.


def _create_taxonomy() -> ProcessTaxonomy:
    """Create the module-level taxonomy singleton.

    Tries to load from the default YAML file first.  If the file is
    missing or invalid, falls back to the built-in ``PROCESS_DEFINITIONS``.
    """
    if DEFAULT_TAXONOMY_PATH.exists():
        try:
            definitions = load_from_yaml(DEFAULT_TAXONOMY_PATH)
            errors = validate_definitions(definitions)
            if errors:
                logger.warning(
                    "Taxonomy YAML at %s has %d validation errors; "
                    "using built-in definitions. First error: %s",
                    DEFAULT_TAXONOMY_PATH,
                    len(errors),
                    errors[0],
                )
            else:
                t = ProcessTaxonomy(definitions)
                t._source_path = DEFAULT_TAXONOMY_PATH
                logger.info(
                    "Taxonomy initialized from YAML: %s (%d processes)",
                    DEFAULT_TAXONOMY_PATH,
                    len(definitions),
                )
                return t
        except Exception as exc:
            logger.warning(
                "Failed to load taxonomy YAML at %s: %s; using built-in definitions",
                DEFAULT_TAXONOMY_PATH,
                exc,
            )
    else:
        logger.debug(
            "No taxonomy YAML found at %s; using built-in definitions",
            DEFAULT_TAXONOMY_PATH,
        )

    return ProcessTaxonomy()


taxonomy: ProcessTaxonomy = _create_taxonomy()
