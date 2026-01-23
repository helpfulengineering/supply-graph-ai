"""
Data models for OKH manifest generation system.

This module defines the core data structures used throughout the generation pipeline,
including enums, dataclasses, and result types. These models provide the foundation
for the multi-layer generation system and support for LLM integration.

The models are designed to be:
- Type-safe with type annotations
- Extensible for new generation layers
- Compatible with async operations
- Well-documented for maintainability

Key Components:
- PlatformType: Supported source platforms
- GenerationQuality: Quality assessment levels
- GenerationLayer: Available generation layers including LLM
- ProjectData: Raw project data from platforms
- FieldGeneration: Individual field extraction results
- LayerConfig: Configuration for all generation layers
- ManifestGeneration: Complete generation results
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
)

if TYPE_CHECKING:
    from ...models.okh import DocumentationType

# Generic type variables
T = TypeVar("T")


class PlatformType(Enum):
    """
    Supported platforms for manifest generation.

    This enum defines the platforms from which project data can be extracted
    for OKH manifest generation. Each platform may have different metadata
    structures and API capabilities.

    Attributes:
        GITHUB: GitHub repositories
        GITLAB: GitLab projects
        CODEBERG: Codeberg repositories
        HACKADAY: Hackaday.io projects
        UNKNOWN: Unknown or unsupported platforms
    """

    GITHUB = "github"
    GITLAB = "gitlab"
    CODEBERG = "codeberg"
    HACKADAY = "hackaday"
    UNKNOWN = "unknown"


class GenerationQuality(Enum):
    """
    Quality levels for generation results.

    This enum defines the quality assessment levels for generated manifest fields.
    Quality is determined by the completeness of required fields and confidence
    scores of extracted information.

    Attributes:
        COMPLETE: All critical elements generated with high confidence
        PARTIAL: Some critical elements missing or low confidence
        INSUFFICIENT: Majority of critical elements missing
        REQUIRES_REVIEW: Significant ambiguities detected requiring human review
    """

    COMPLETE = auto()  # All critical elements generated
    PARTIAL = auto()  # Some critical elements missing
    INSUFFICIENT = auto()  # Majority of critical elements missing
    REQUIRES_REVIEW = auto()  # Significant ambiguities detected


class AnalysisDepth(Enum):
    """
    Configurable content analysis depth levels for file categorization.

    Defines how deeply to analyze file content when categorizing files:
    - SHALLOW: Fast, low cost - First 500 chars, keyword matching (default)
    - MEDIUM: Moderate cost, better accuracy - First 2000 chars, structure analysis
    - DEEP: Higher cost, maximum accuracy - Full document, semantic analysis
    """

    SHALLOW = "shallow"  # Default: First 500 chars, keyword matching
    MEDIUM = "medium"  # First 2000 chars, structure analysis
    DEEP = "deep"  # Full document, semantic analysis


class GenerationLayer(Enum):
    """
    Available generation layers in the multi-layer processing pipeline.

    This enum defines the different layers used for progressive enhancement
    of manifest generation. Each layer applies different techniques to extract
    and enhance field information from project data.

    Processing Order:
    1. DIRECT: Direct field mapping from platform metadata
    2. HEURISTIC: Rule-based pattern recognition and file analysis
    3. NLP: Natural language processing for semantic understanding
    4. LLM: Large language model for advanced content analysis
    5. BOM_NORMALIZATION: Bill of Materials processing and structuring
    6. USER_EDIT: User manual editing and validation

    Attributes:
        DIRECT: Direct field mapping from platform APIs and metadata
        HEURISTIC: Rule-based pattern recognition and file structure analysis
        NLP: Natural language processing using spaCy for semantic understanding
        LLM: Large language model for advanced content analysis and generation
        BOM_NORMALIZATION: BOM processing, normalization, and structuring
        USER_EDIT: User manual editing and validation of generated content
    """

    DIRECT = "direct"  # Direct field mapping
    HEURISTIC = "heuristic"  # Rule-based pattern recognition
    NLP = "nlp"  # Natural language processing
    LLM = "llm"  # Large language model
    BOM_NORMALIZATION = "bom_normalization"  # BOM normalization and structuring
    USER_EDIT = "user_edit"  # User manual editing


@dataclass
class FileInfo:
    """
    Information about a project file.

    This dataclass represents metadata and content for a single file
    within a project. It's used by generation layers to analyze
    file structure and extract information.

    Attributes:
        path: Relative path to the file within the project
        size: File size in bytes
        content: File content as string (for text files)
        file_type: Detected file type (e.g., 'markdown', 'image', 'code')
    """

    path: str
    size: int
    content: str
    file_type: str


@dataclass
class DocumentInfo:
    """
    Information about project documentation.

    This dataclass represents structured documentation within a project,
    such as README files, manuals, or other documentation content.

    Attributes:
        title: Title or name of the document
        path: Path to the document file
        doc_type: Type of document (e.g., 'readme', 'manual', 'guide')
        content: Document content as string
    """

    title: str
    path: str
    doc_type: str
    content: str


@dataclass
class ProjectData:
    """
    Raw project data extracted from a platform.

    This dataclass contains all the raw data extracted from a source platform
    (GitHub, GitLab, etc.) that will be processed by the generation layers
    to create an OKH manifest.

    Attributes:
        platform: Source platform type (GitHub, GitLab, etc.)
        url: URL of the project/repository
        metadata: Platform-specific metadata (API responses, etc.)
        files: List of project files with content and metadata
        documentation: List of structured documentation files
        raw_content: Raw content from platform APIs (for debugging/fallback)
    """

    platform: PlatformType
    url: str
    metadata: Dict[str, Any]
    files: List[FileInfo]
    documentation: List[DocumentInfo]
    raw_content: Dict[str, str]


@dataclass
class RepositoryAssessment:
    """
    Assessment of repository size, structure, and complexity.

    This dataclass provides information about a repository's structure
    to help with efficient processing, especially for large repositories.

    Attributes:
        total_files: Total number of files in the repository
        total_directories: Total number of directories in the repository
        file_types: Dictionary mapping file types to counts
        directory_tree: Dictionary mapping directory paths to file lists
    """

    total_files: int = 0
    total_directories: int = 0
    file_types: Dict[str, int] = field(default_factory=dict)
    directory_tree: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class RouteEntry:
    """
    Entry in the repository routing table.

    Represents a mapping from a source file path to an OKH destination.

    Attributes:
        source_path: Original file path in repository
        destination_type: DocumentationType for the destination
        destination_path: Destination path in OKH structure
        confidence: Confidence score for this route (0.0 to 1.0)
    """

    source_path: str
    destination_type: "DocumentationType"  # Forward reference
    destination_path: str
    confidence: float = 0.0


@dataclass
class RepositoryRoutingTable:
    """
    Routing table mapping repository files to OKH model destinations.

    This dataclass acts as a central coordination point for file categorization,
    mapping repository file paths to their destinations in the OKH manifest structure.
    It can be updated iteratively by multiple processes (Layer 1, Layer 2, etc.).

    Attributes:
        routes: Dictionary mapping source paths to RouteEntry objects
        metadata: Additional metadata about the routing table
    """

    routes: Dict[str, RouteEntry] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_route(
        self,
        source_path: str,
        destination_type: "DocumentationType",
        destination_path: str,
        confidence: float = 0.0,
    ) -> None:
        """
        Add or update a route in the routing table.

        Args:
            source_path: Original file path in repository
            destination_type: DocumentationType for the destination
            destination_path: Destination path in OKH structure
            confidence: Confidence score for this route
        """
        self.routes[source_path] = RouteEntry(
            source_path=source_path,
            destination_type=destination_type,
            destination_path=destination_path,
            confidence=confidence,
        )

    def get_route(self, source_path: str) -> Optional[RouteEntry]:
        """
        Get a route by source path.

        Args:
            source_path: Source file path

        Returns:
            RouteEntry or None if not found
        """
        return self.routes.get(source_path)

    def get_routes_by_type(
        self, destination_type: "DocumentationType"
    ) -> Dict[str, RouteEntry]:
        """
        Get all routes for a specific documentation type.

        Args:
            destination_type: DocumentationType to filter by

        Returns:
            Dictionary of routes matching the type
        """
        return {
            path: route
            for path, route in self.routes.items()
            if route.destination_type == destination_type
        }


@dataclass
class FieldGeneration:
    """
    Individual field generation result with metadata.

    This dataclass represents the result of extracting a single field
    from project data, including the extracted value, confidence score,
    and metadata about how it was generated.

    Attributes:
        value: The extracted field value (type depends on field)
        confidence: Confidence score between 0.0 and 1.0
        source_layer: Which generation layer produced this result
        generation_method: Specific method used for extraction
        raw_source: Raw source data used for extraction (for debugging)
    """

    value: Any
    confidence: float
    source_layer: GenerationLayer
    generation_method: str
    raw_source: str


@dataclass
class GenerationMetadata:
    """Metadata about the generation process"""

    generation_timestamp: datetime = field(default_factory=datetime.now)
    source_url: Optional[str] = None
    generation_quality: GenerationQuality = GenerationQuality.INSUFFICIENT
    flags: List[str] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    processing_logs: List[str] = field(default_factory=list)

    def add_processing_log(self, message: str) -> None:
        """Add a processing log entry"""
        self.processing_logs.append(message)

    def update_confidence(self, field: str, score: float) -> None:
        """Update confidence score for a specific field"""
        self.confidence_scores[field] = max(0.0, min(1.0, score))


@dataclass
class QualityReport:
    """Assessment of generation quality"""

    overall_quality: float
    required_fields_complete: bool
    missing_required_fields: List[str]
    low_confidence_fields: List[str]
    recommendations: List[str]


@dataclass
class ManifestGeneration:
    """Complete manifest generation result"""

    project_data: ProjectData
    generated_fields: Dict[str, FieldGeneration]
    confidence_scores: Dict[str, float]
    quality_report: QualityReport
    missing_fields: List[str]
    full_bom: Optional[Any] = None  # Store full BillOfMaterials object for export
    unified_bom_mode: bool = False  # Whether to include full BOM in manifest
    include_file_metadata: bool = False  # Whether to include metadata in file entries

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        # Convert generated fields to simple dict
        fields_dict = {}
        for field_name, field_gen in self.generated_fields.items():
            fields_dict[field_name] = field_gen.value

        # Add quality report
        quality_dict = {
            "overall_quality": self.quality_report.overall_quality,
            "required_fields_complete": self.quality_report.required_fields_complete,
            "missing_required_fields": self.quality_report.missing_required_fields,
            "low_confidence_fields": self.quality_report.low_confidence_fields,
            "recommendations": self.quality_report.recommendations,
        }

        return {
            "title": fields_dict.get("title", "Unknown"),
            "version": fields_dict.get("version", "1.0.0"),
            "repo": fields_dict.get("repo", ""),
            "license": fields_dict.get("license", ""),
            "description": fields_dict.get("description", ""),
            "confidence_scores": self.confidence_scores,
            "missing_fields": self.missing_fields,
        }

    def to_okh_manifest(self) -> Dict[str, Any]:
        """Convert to proper OKH manifest format"""
        import uuid
        from datetime import datetime

        # Convert generated fields to simple dict
        fields_dict = {}
        for field_name, field_gen in self.generated_fields.items():
            fields_dict[field_name] = field_gen.value

        # Generate deterministic UUID based on repo URL
        repo_url = fields_dict.get("repo", "")
        if repo_url:
            # Create deterministic UUID from repo URL
            namespace = uuid.NAMESPACE_URL
            manifest_id = str(uuid.uuid5(namespace, repo_url))
        else:
            manifest_id = str(uuid.uuid4())

        # Build proper OKH manifest structure
        manifest = {
            "okhv": "OKH-LOSHv1.0",
            "id": manifest_id,
            "title": fields_dict.get("title", "Unknown"),
            "repo": fields_dict.get("repo", ""),
            "version": fields_dict.get("version", "1.0.0"),
            "license": self._normalize_license(
                fields_dict.get("license"), self.project_data
            ),
            "description": fields_dict.get("description", ""),
            "function": fields_dict.get("function", ""),
            "intended_use": fields_dict.get("intended_use", ""),
            "keywords": fields_dict.get("keywords", []),
            "contact": fields_dict.get("contact", {}),
            "organization": fields_dict.get("organization", {}),
            "development_stage": fields_dict.get("development_stage", "development"),
            "technology_readiness_level": fields_dict.get(
                "technology_readiness_level", "TRL-1"
            ),
            "manufacturing_files": self._remove_type_from_file_entries(
                fields_dict.get("manufacturing_files", [])
            ),
            "design_files": self._remove_type_from_file_entries(
                fields_dict.get("design_files", [])
            ),
            "making_instructions": self._remove_type_from_file_entries(
                fields_dict.get("making_instructions", [])
            ),
            "operating_instructions": self._remove_type_from_file_entries(
                fields_dict.get("operating_instructions", [])
            ),
            "technical_specifications": self._remove_type_from_file_entries(
                fields_dict.get("technical_specifications", [])
            ),
            "publications": self._remove_type_from_file_entries(
                fields_dict.get("publications", [])
            ),
            "tool_list": fields_dict.get("tool_list", []),
            "manufacturing_processes": fields_dict.get("manufacturing_processes", []),
            "materials": self._normalize_materials(
                fields_dict.get("materials", []), self.full_bom
            ),
            "manufacturing_specs": self._generate_manufacturing_specs(
                fields_dict, self.project_data
            ),
            "bom": self._get_bom_field(fields_dict),
            "standards_used": fields_dict.get("standards_used", []),
            "tsdc": fields_dict.get("tsdc", []),
            "parts": (
                self._extract_parts_from_bom(self.full_bom, fields_dict)
                if self.full_bom
                else fields_dict.get("parts", [])
            ),
            "sub_parts": fields_dict.get("sub_parts", []),
            "software": self._normalize_software(
                fields_dict.get("software", []), self.project_data
            ),
            "metadata": {
                "generated_at": datetime.now().isoformat() + "Z",
                "generation_confidence": round(self.quality_report.overall_quality, 2),
                "missing_required_fields": self.missing_fields,
                "generation_method": "automated_extraction",
            },
        }

        # Add optional fields if they exist (with normalization)
        if (
            "documentation_language" in fields_dict
            and fields_dict["documentation_language"]
        ):
            manifest["documentation_language"] = fields_dict["documentation_language"]
        if "contact" in fields_dict and fields_dict["contact"]:
            manifest["contact"] = fields_dict["contact"]
        if "organization" in fields_dict and fields_dict["organization"]:
            manifest["organization"] = fields_dict["organization"]

        # Normalize licensor (required field)
        licensor_value = fields_dict.get("licensor")
        manifest["licensor"] = self._normalize_licensor(
            licensor_value, fields_dict, self.project_data
        )

        if (
            "documentation_language" not in manifest
            or not manifest["documentation_language"]
        ):
            manifest["documentation_language"] = "en"  # Default to English

        return manifest

    def _remove_type_from_file_entries(
        self, file_list: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Remove redundant 'type' field from file entries.

        Since files are already categorized into specific lists (design_files,
        manufacturing_files, etc.), the 'type' field is redundant and can be
        safely removed to reduce manifest size.

        Args:
            file_list: List of file entries (dicts or DocumentRef objects)

        Returns:
            List of file entries with 'type' field removed
        """
        if not file_list:
            return []

        cleaned_list = []
        for entry in file_list:
            if isinstance(entry, dict):
                # Create a copy without the 'type' field
                cleaned_entry = {k: v for k, v in entry.items() if k != "type"}
                cleaned_list.append(cleaned_entry)
            elif hasattr(entry, "to_dict"):
                # Handle DocumentRef objects
                entry_dict = entry.to_dict()
                cleaned_entry = {k: v for k, v in entry_dict.items() if k != "type"}
                cleaned_list.append(cleaned_entry)
            else:
                # Unknown type, pass through as-is
                cleaned_list.append(entry)

        return cleaned_list

    def _normalize_license(
        self, license_value: Any, project_data: ProjectData
    ) -> Dict[str, Any]:
        """
        Normalize license to License object format.

        Converts various license input formats to the schema-compliant
        License object with hardware, documentation, and software fields.

        Args:
            license_value: License value from generated fields (string, dict, or None)
            project_data: Project data for extracting license from files

        Returns:
            Dictionary with hardware, documentation, and software license fields
        """
        # If already a dict with correct structure, return it
        if isinstance(license_value, dict):
            if all(
                k in license_value for k in ["hardware", "documentation", "software"]
            ):
                return license_value
            # If dict with single "license" key, extract and apply to all
            if "license" in license_value:
                single_license = license_value["license"]
                return {
                    "hardware": single_license,
                    "documentation": single_license,
                    "software": single_license,
                }

        # If string, try to extract from LICENSE file or use as default for all
        if isinstance(license_value, str):
            # Try to find LICENSE file in project data
            license_from_file = self._extract_license_from_files(project_data)
            if license_from_file:
                # For now, use the string value for all three fields
                # TODO: Parse LICENSE file to extract separate licenses
                return {
                    "hardware": license_value,
                    "documentation": license_value,
                    "software": license_value,
                }
            else:
                # Use string as default for all three fields
                return {
                    "hardware": license_value,
                    "documentation": license_value,
                    "software": license_value,
                }

        # Default fallback: empty License object
        return {"hardware": None, "documentation": None, "software": None}

    def _extract_license_from_files(self, project_data: ProjectData) -> Optional[str]:
        """
        Extract license from LICENSE files in project data.

        Args:
            project_data: Project data containing files

        Returns:
            License string if found, None otherwise
        """
        # Look for LICENSE files
        license_file_patterns = ["LICENSE", "LICENSE.txt", "LICENSE.md", "LICENCE"]
        for file_info in project_data.files:
            filename = file_info.path.split("/")[-1]
            if filename in license_file_patterns:
                # Return first 100 chars as identifier (SPDX format)
                if file_info.content:
                    return file_info.content[:100].strip()
        return None

    def _normalize_licensor(
        self,
        licensor_value: Any,
        fields_dict: Dict[str, Any],
        project_data: ProjectData,
    ) -> Any:
        """
        Normalize licensor to Person/Organization object format.

        Converts various licensor input formats to schema-compliant
        Person or Organization object.

        Args:
            licensor_value: Licensor value from generated fields (string, dict, or None)
            fields_dict: Dictionary of all generated fields
            project_data: Project data for extracting metadata

        Returns:
            Person/Organization dict or string (fallback)
        """
        # If already a Person/Organization object dict, return it
        if isinstance(licensor_value, dict) and "name" in licensor_value:
            return licensor_value

        # If string, try to enrich from organization or repository metadata
        if isinstance(licensor_value, str):
            # First, try to match with organization field
            org = fields_dict.get("organization", {})
            if isinstance(org, dict) and org.get("name") == licensor_value:
                # Use organization as licensor
                return {
                    "name": org.get("name", licensor_value),
                    "url": org.get("url"),
                    "email": org.get("email"),
                }

            # Try to extract from repository metadata
            repo_metadata = project_data.metadata.get("owner", {})
            if repo_metadata and repo_metadata.get("name") == licensor_value:
                return {
                    "name": repo_metadata.get("name", licensor_value),
                    "url": repo_metadata.get("html_url") or repo_metadata.get("url"),
                    "email": repo_metadata.get("email"),
                }

            # Fallback: simple Person object with just name
            return {"name": licensor_value}

        # If missing, try to extract from organization or repo URL
        if not licensor_value:
            org = fields_dict.get("organization", {})
            if isinstance(org, dict) and org.get("name"):
                return {
                    "name": org.get("name"),
                    "url": org.get("url"),
                    "email": org.get("email"),
                }

            # Try repository metadata
            repo_metadata = project_data.metadata.get("owner", {})
            if repo_metadata and repo_metadata.get("name"):
                return {
                    "name": repo_metadata.get("name"),
                    "url": repo_metadata.get("html_url") or repo_metadata.get("url"),
                    "email": repo_metadata.get("email"),
                }

            # Try to extract from repo URL
            repo_url = fields_dict.get("repo", "")
            if repo_url:
                if "github.com/" in repo_url:
                    parts = repo_url.split("github.com/")[-1].split("/")
                    if len(parts) >= 1:
                        return {"name": parts[0]}
                elif "gitlab.com/" in repo_url:
                    parts = repo_url.split("gitlab.com/")[-1].split("/")
                    if len(parts) >= 1:
                        return {"name": parts[0]}

            # Final fallback
            return {"name": "Unknown"}

        # Return as-is if already correct format or unknown type
        return licensor_value

    def _normalize_materials(
        self, materials_value: Any, bom: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Normalize materials to MaterialSpec array format.

        Converts string arrays to MaterialSpec objects with required
        material_id and name fields.

        Args:
            materials_value: Materials value from generated fields (list of strings or MaterialSpec dicts)
            bom: Optional BOM object to extract additional materials from

        Returns:
            List of MaterialSpec dictionaries
        """
        materials = []

        # If already MaterialSpec objects (dicts with material_id)
        if isinstance(materials_value, list) and materials_value:
            if (
                isinstance(materials_value[0], dict)
                and "material_id" in materials_value[0]
            ):
                return materials_value  # Already correct format

        # If string array, convert to MaterialSpec
        if isinstance(materials_value, list):
            for mat in materials_value:
                if isinstance(mat, str):
                    material_id = self._generate_material_id(mat)
                    materials.append(
                        {
                            "material_id": material_id,
                            "name": mat,
                            "quantity": None,
                            "unit": None,
                            "notes": None,
                        }
                    )
                elif isinstance(mat, dict):
                    # If dict but missing material_id, add it
                    if "material_id" not in mat and "name" in mat:
                        mat["material_id"] = self._generate_material_id(mat["name"])
                    materials.append(mat)

        # TODO: Extract from BOM if available
        # This will be implemented when BOM structure is better understood

        return materials

    def _generate_material_id(self, name: str) -> str:
        """
        Generate material_id from material name.

        Creates a slug-like identifier from the material name.

        Args:
            name: Material name

        Returns:
            Material ID string (e.g., "mat-aluminum")
        """
        import re

        # Create slug from name
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
        slug = slug.strip("-")
        # Ensure it starts with "mat-"
        if not slug.startswith("mat-"):
            slug = f"mat-{slug}"
        return slug

    def _normalize_software(
        self, software_value: Any, project_data: ProjectData
    ) -> List[Dict[str, Any]]:
        """
        Normalize software to Software object array format.

        Converts DocumentRef entries to Software objects with required
        release field and optional installation_guide.

        Args:
            software_value: Software value from generated fields (list of DocumentRef dicts or Software dicts)
            project_data: Project data for finding installation guides

        Returns:
            List of Software dictionaries
        """
        software_list = []

        # If already Software objects (dicts with release field)
        if isinstance(software_value, list) and software_value:
            if isinstance(software_value[0], dict) and "release" in software_value[0]:
                return software_value  # Already correct format

        # If DocumentRef array, convert to Software objects
        if isinstance(software_value, list):
            # Extract version once (shared for all software entries)
            version = self._extract_software_version(project_data)

            # Track seen entries to avoid duplicates
            seen_entries = set()

            for item in software_value:
                if isinstance(item, dict):
                    # Check if it's a DocumentRef (has type field)
                    if "type" in item and item.get("type") == "software":
                        # Convert DocumentRef to Software
                        if version:
                            release = version
                        else:
                            # Fallback to file path if no version found
                            release = item.get("path", item.get("title", "unknown"))

                        # Try to find installation guide
                        installation_guide = self._find_installation_guide(
                            item.get("path"), project_data
                        )

                        # Create entry
                        software_entry = {
                            "release": release,
                            "installation_guide": installation_guide,
                        }

                        # De-duplicate: use (release, installation_guide) as key
                        entry_key = (release, installation_guide)
                        if entry_key not in seen_entries:
                            seen_entries.add(entry_key)
                            software_list.append(software_entry)
                    # If it's already a Software object (has release), use it
                    elif "release" in item:
                        # Also de-duplicate existing Software objects
                        entry_key = (
                            item.get("release"),
                            item.get("installation_guide"),
                        )
                        if entry_key not in seen_entries:
                            seen_entries.add(entry_key)
                            software_list.append(item)

        return software_list

    def _find_installation_guide(
        self, software_path: Optional[str], project_data: ProjectData
    ) -> Optional[str]:
        """
        Find installation guide for a software component.

        Looks for common installation guide patterns near the software path.

        Args:
            software_path: Path to the software file
            project_data: Project data containing files

        Returns:
            Path to installation guide if found, None otherwise
        """
        if not software_path:
            return None

        # Look for installation guides in common locations
        guide_patterns = [
            "INSTALL.md",
            "INSTALLATION.md",
            "INSTALL.txt",
            "README.md",  # Often contains installation instructions
            "docs/installation.md",
            "docs/install.md",
        ]

        # Check files in project data
        for file_info in project_data.files:
            filename = file_info.path.split("/")[-1]
            if filename in guide_patterns:
                return file_info.path

        return None

    def _extract_software_version(self, project_data: ProjectData) -> Optional[str]:
        """
        Extract software version from package files.

        Tries to extract version from:
        1. package.json (Node.js projects)
        2. pyproject.toml (Python projects)
        3. setup.py (Python projects)
        4. setup.cfg (Python projects)

        Args:
            project_data: Project data containing files

        Returns:
            Version string if found, None otherwise
        """
        import json
        import re

        # Try package.json (Node.js)
        for file_info in project_data.files:
            if file_info.path.endswith("package.json"):
                try:
                    package_data = json.loads(file_info.content)
                    version = package_data.get("version")
                    if version:
                        return str(version)
                except (json.JSONDecodeError, AttributeError):
                    continue

        # Try pyproject.toml (Python)
        for file_info in project_data.files:
            if file_info.path.endswith("pyproject.toml"):
                try:
                    # Simple TOML parsing for version field
                    # Look for [project] section with version
                    content = file_info.content
                    # Match: version = "1.2.3" or version = '1.2.3'
                    version_match = re.search(
                        r'version\s*=\s*["\']([^"\']+)["\']', content
                    )
                    if version_match:
                        return version_match.group(1)
                    # Also try [tool.poetry] or [tool.setuptools]
                    for section in ["[project]", "[tool.poetry]", "[tool.setuptools]"]:
                        if section in content:
                            # Extract version from this section
                            section_match = re.search(
                                rf'{re.escape(section)}.*?version\s*=\s*["\']([^"\']+)["\']',
                                content,
                                re.DOTALL,
                            )
                            if section_match:
                                return section_match.group(1)
                except (AttributeError, Exception):
                    continue

        # Try setup.py (Python)
        for file_info in project_data.files:
            if file_info.path.endswith("setup.py"):
                try:
                    content = file_info.content
                    # Match: version="1.2.3" or version='1.2.3' or version = "1.2.3"
                    version_match = re.search(
                        r'version\s*=\s*["\']([^"\']+)["\']', content
                    )
                    if version_match:
                        return version_match.group(1)
                except (AttributeError, Exception):
                    continue

        # Try setup.cfg (Python)
        for file_info in project_data.files:
            if file_info.path.endswith("setup.cfg"):
                try:
                    content = file_info.content
                    # Match: version = 1.2.3
                    version_match = re.search(
                        r"version\s*=\s*([^\n]+)", content, re.IGNORECASE
                    )
                    if version_match:
                        version = version_match.group(1).strip()
                        # Remove quotes if present
                        version = version.strip("\"'")
                        if version:
                            return version
                except (AttributeError, Exception):
                    continue

        return None

    def _clean_part_name(self, name: str) -> str:
        """
        Clean and normalize part name from BOM.

        Extracts the actual part name from sentence fragments and instructions.
        Only applies aggressive cleaning if the name looks like a sentence fragment.
        Preserves already-clean names.

        For example:
        - "degree header pins, then use needle nose pilers..." → "header pins"
        - "screw terminals on Relay Board. Then insert..." → "screw terminals"
        - "M3 screws to install it on the outside of the case." → "M3 screws"
        - "reactor-manifold" → "reactor-manifold" (preserved)

        Args:
            name: Raw component name (may be a sentence fragment or instruction)

        Returns:
            Cleaned part name
        """
        import re

        if not name:
            return "Unknown"

        # Remove leading/trailing whitespace
        name = name.strip()

        # Check if name looks like a sentence fragment (needs cleaning)
        # Indicators: contains "then", "to install", "and the", long sentences, etc.
        needs_cleaning = (
            len(name) > 60  # Very long names are likely sentences
            or ", then" in name.lower()
            or ". then" in name.lower()
            or " to install" in name.lower()
            or " to " in name.lower()
            and len(name) > 30
            or " and the " in name.lower()
            or (name.count(",") > 0 and len(name) > 40)
            or (name.count(".") > 0 and len(name) > 40)
        )

        # If name is already clean, return as-is (preserve case)
        if not needs_cleaning:
            return name

        # Apply aggressive cleaning for sentence fragments
        original_name = name

        # Remove common instruction phrases at the start
        instruction_prefixes = [
            r"^degree\s+",  # "degree header pins"
            r"^then\s+use\s+",  # "then use..."
            r"^then\s+insert\s+",  # "then insert..."
            r"^to\s+install\s+",  # "to install..."
            r"^to\s+",  # "to..."
        ]
        for prefix in instruction_prefixes:
            name = re.sub(prefix, "", name, flags=re.IGNORECASE)

        # Extract part name before first comma, period, or instruction word
        # Look for common part name patterns
        # Pattern 1: "M3 screws" or "M4 bolts" (screw/bolt specifications)
        screw_match = re.search(
            r"([M\d]+(?:\s*[xX]\s*\d+)?\s*(?:screws?|bolts?|nuts?|washers?))",
            name,
            re.IGNORECASE,
        )
        if screw_match:
            return screw_match.group(1).strip()

        # Pattern 2: "header pins", "jumper wires", "screw terminals" (component types)
        component_match = re.search(
            r"((?:header\s+)?pins?|(?:jumper\s+)?wires?|(?:screw\s+)?terminals?|connectors?|cables?|wires?)",
            name,
            re.IGNORECASE,
        )
        if component_match:
            return component_match.group(1).strip()

        # Pattern 3: Extract first noun phrase (usually the part name)
        # Split on common separators and take the first meaningful phrase
        separators = [",", ".", " then ", " to ", " and ", " or "]
        for sep in separators:
            if sep in name:
                parts = name.split(sep, 1)
                first_part = parts[0].strip()
                # If first part is meaningful (not just "degree" or "then")
                if len(first_part) > 3 and not first_part.lower() in [
                    "then",
                    "and",
                    "or",
                    "to",
                    "the",
                ]:
                    name = first_part
                    break

        # Remove trailing instruction words
        instruction_suffixes = [
            r"\s+to\s+.*$",  # "screws to install..."
            r"\s+then\s+.*$",  # "pins then use..."
            r"\s+and\s+.*$",  # "pins and the other..."
            r"\s+on\s+the\s+.*$",  # "screws on the outside..."
        ]
        for suffix in instruction_suffixes:
            name = re.sub(suffix, "", name, flags=re.IGNORECASE)

        # Clean up: remove extra whitespace
        name = re.sub(r"\s+", " ", name).strip()

        # If result is too short or still looks like a sentence, try to extract key words
        if len(name) < 3 or "." in name or "," in name:
            # Extract key words: look for common part terms
            key_terms = [
                r"\b(screws?|bolts?|nuts?|washers?)\b",
                r"\b(pins?|headers?)\b",
                r"\b(wires?|cables?|jumpers?)\b",
                r"\b(terminals?|connectors?)\b",
                r"\b(M\d+)\b",  # M3, M4, etc.
            ]
            for term_pattern in key_terms:
                matches = re.findall(term_pattern, original_name, re.IGNORECASE)
                if matches:
                    # Combine with preceding word if it's a modifier (e.g., "header pins")
                    for i, match in enumerate(matches):
                        if i > 0:
                            prev_word = re.search(
                                rf"\w+\s+{re.escape(match)}",
                                original_name,
                                re.IGNORECASE,
                            )
                            if prev_word:
                                return prev_word.group(0).strip()
                    result = (
                        matches[0]
                        if isinstance(matches[0], str)
                        else " ".join(matches[:2])
                    )
                    # Preserve original case for the matched term
                    if result:
                        return result

        # Final fallback: return first 50 characters, cleaned
        if len(name) > 50:
            name = name[:50].rsplit(" ", 1)[0]  # Cut at word boundary

        return name if name else "Unknown"

    def _generate_part_id(self, name: str, original_id: str) -> str:
        """
        Generate a UUID part ID from a cleaned name.

        Creates a deterministic UUID from the part name to ensure:
        - Valid UUID format (required by PartSpec)
        - Deterministic (same name = same UUID)
        - Uniqueness (includes original_id in hash if needed)

        Args:
            name: Cleaned part name
            original_id: Original component ID (for uniqueness fallback)

        Returns:
            Valid UUID string (e.g., "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        """
        import hashlib

        from ..validation.uuid_validator import UUIDValidator

        # Create a unique identifier string from name and original_id
        # This ensures deterministic UUIDs while maintaining uniqueness
        if not name or name == "Unknown":
            # Fallback: use original_id to ensure uniqueness
            if original_id:
                unique_string = f"part:{original_id}"
            else:
                unique_string = "part:unknown"
        else:
            # Use name as primary identifier, with original_id for uniqueness
            # Include original_id to handle cases where multiple components have same name
            if original_id:
                unique_string = f"part:{name}:{original_id}"
            else:
                unique_string = f"part:{name}"

        # Generate deterministic UUID from the unique string
        return UUIDValidator.generate_uuid_from_string(unique_string)

    def _extract_parts_from_bom(
        self, bom: Any, fields_dict: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract parts from BOM and convert to PartSpec format.

        Converts BOM Component objects to PartSpec dictionaries with
        required fields (name, id) and optional fields extracted from
        component metadata.

        Args:
            bom: BillOfMaterials object with components
            fields_dict: Dictionary of generated fields for linking files

        Returns:
            List of PartSpec dictionaries
        """
        import uuid

        parts = []

        # Check if BOM has components
        if not bom:
            return parts

        # Handle both BillOfMaterials object and dict
        if hasattr(bom, "components"):
            components = bom.components
        elif isinstance(bom, dict) and "components" in bom:
            components = bom["components"]
        else:
            return parts

        # Convert each component to PartSpec
        for component in components:
            # Handle both Component object and dict
            if hasattr(component, "name"):
                comp_name = component.name
                comp_id = getattr(component, "id", None) or str(uuid.uuid4())
                comp_metadata = getattr(component, "metadata", {})
                comp_requirements = getattr(component, "requirements", {})
                comp_reference = getattr(component, "reference", None)
            elif isinstance(component, dict):
                comp_name = component.get("name", "Unknown")
                comp_id = component.get("id") or str(uuid.uuid4())
                comp_metadata = component.get("metadata", {})
                comp_requirements = component.get("requirements", {})
                comp_reference = component.get("reference")
            else:
                continue

            # Clean and normalize part name (extract actual part name from sentence fragments)
            cleaned_name = self._clean_part_name(comp_name)

            # Generate clean ID from cleaned name (not original sentence fragment)
            # If the name was cleaned, generate new ID; otherwise use original if it's reasonable
            if cleaned_name != comp_name:
                # Name was cleaned, generate new ID from cleaned name
                clean_id = self._generate_part_id(cleaned_name, comp_id)
            else:
                # Name wasn't cleaned, but check if original ID is reasonable
                # If ID is too long (sentence fragment), regenerate from name
                if len(comp_id) > 50 or "__" in comp_id:
                    clean_id = self._generate_part_id(cleaned_name, comp_id)
                else:
                    clean_id = comp_id if isinstance(comp_id, str) else str(comp_id)

            # Create PartSpec dict
            part = {
                "id": clean_id,
                "name": cleaned_name,
                "source": [],
                "export": [],
                "auxiliary": [],
            }

            # Extract material from metadata
            if "material" in comp_metadata:
                part["material"] = comp_metadata["material"]

            # Extract tsdc from metadata or requirements
            tsdc_list = comp_metadata.get("tsdc", [])
            if not tsdc_list and "tsdc" in comp_requirements:
                tsdc_list = comp_requirements["tsdc"]
            if isinstance(tsdc_list, list):
                part["tsdc"] = tsdc_list
            else:
                part["tsdc"] = []

            # Extract manufacturing params
            part["manufacturing_params"] = comp_requirements.get(
                "manufacturing_params", {}
            )

            # Extract source/export from reference or link to design files
            if comp_reference:
                if isinstance(comp_reference, dict):
                    if "source" in comp_reference:
                        part["source"] = (
                            [comp_reference["source"]]
                            if isinstance(comp_reference["source"], str)
                            else comp_reference["source"]
                        )
                    if "export" in comp_reference:
                        part["export"] = (
                            [comp_reference["export"]]
                            if isinstance(comp_reference["export"], str)
                            else comp_reference["export"]
                        )

            # Use improved file linking algorithm
            design_files = fields_dict.get("design_files", [])
            manufacturing_files = fields_dict.get("manufacturing_files", [])

            # Link files using stricter matching
            linked_source = self._link_part_to_files(
                comp_name, comp_metadata, design_files, is_manufacturing=False
            )
            linked_export = self._link_part_to_files(
                comp_name, comp_metadata, manufacturing_files, is_manufacturing=True
            )

            if linked_source:
                if not part["source"]:
                    part["source"] = []
                part["source"].extend(linked_source)

            if linked_export:
                if not part["export"]:
                    part["export"] = []
                part["export"].extend(linked_export)

            parts.append(part)

        return parts

    def _link_part_to_files(
        self,
        comp_name: str,
        comp_metadata: Dict[str, Any],
        file_list: List[Any],
        is_manufacturing: bool = False,
    ) -> List[str]:
        """
        Link component to files using improved, stricter matching algorithm.

        Uses multiple strategies in priority order:
        1. Directory structure matching (parts/{component-name}/)
        2. Filename matching (component name in filename)
        3. BOM metadata hints (file_reference, file_path)
        4. Prioritizes CAD files over documentation

        Args:
            comp_name: Component name
            comp_metadata: Component metadata from BOM
            file_list: List of file dictionaries (design_files or manufacturing_files)
            is_manufacturing: Whether these are manufacturing files (export) or design files (source)

        Returns:
            List of file paths that match the component
        """
        import re
        from pathlib import Path

        if not file_list:
            return []

        linked_files = []
        comp_name_lower = comp_name.lower().strip()

        # Normalize component name: remove parentheses, special chars, extract key words
        comp_normalized = re.sub(r"[()]", "", comp_name_lower)
        comp_words = [w for w in re.split(r"[^a-z0-9]+", comp_normalized) if len(w) > 2]

        # Extract hints from metadata
        file_reference = comp_metadata.get("file_reference", "").lower()
        file_path_hint = comp_metadata.get("file_path", "").lower()

        # CAD file extensions (prioritized)
        cad_extensions = [
            ".stl",
            ".step",
            ".stp",
            ".obj",
            ".ply",
            ".3mf",
            ".cad",
            ".dxf",
        ]
        # Documentation extensions (lower priority)
        doc_extensions = [".md", ".txt", ".pdf", ".doc", ".docx"]

        # Strategy 1: Directory structure matching (highest priority)
        # Look for files in parts/{component-name}/ or parts/{key-word}/
        for file_item in file_list:
            if not isinstance(file_item, dict):
                continue

            file_path = file_item.get("path", "")
            if not file_path:
                continue

            file_path_lower = file_path.lower()
            path_obj = Path(file_path_lower)

            # Only match files in parts/ directory (stricter requirement)
            if "parts/" not in file_path_lower:
                continue

            # Extract directory name from parts/{dir}/
            parts_match = re.search(r"parts/([^/]+)", file_path_lower)
            if not parts_match:
                continue

            dir_name = parts_match.group(1)

            # Check if component name or key words match directory
            if self._matches_component(comp_name_lower, comp_words, dir_name):
                if file_path not in linked_files:
                    linked_files.append(file_path)
                    continue

            # Check if file_reference matches directory
            if file_reference and file_reference in dir_name:
                if file_path not in linked_files:
                    linked_files.append(file_path)
                    continue

        # Strategy 2: Filename matching (if no directory matches found)
        if not linked_files:
            for file_item in file_list:
                if not isinstance(file_item, dict):
                    continue

                file_path = file_item.get("path", "")
                if not file_path:
                    continue

                file_path_lower = file_path.lower()
                path_obj = Path(file_path_lower)
                filename = path_obj.stem.lower()  # filename without extension

                # Only match files in parts/ directory
                if "parts/" not in file_path_lower:
                    continue

                # Check if component name or key words match filename
                if self._matches_component(comp_name_lower, comp_words, filename):
                    if file_path not in linked_files:
                        linked_files.append(file_path)

        # Strategy 3: Use file_reference hint (e.g., "Heat" -> "heat" -> "blue-heat")
        if not linked_files and file_reference:
            for file_item in file_list:
                if not isinstance(file_item, dict):
                    continue

                file_path = file_item.get("path", "")
                if not file_path:
                    continue

                file_path_lower = file_path.lower()

                # Only match files in parts/ directory
                if "parts/" not in file_path_lower:
                    continue

                # Check if file_reference appears in path
                if file_reference in file_path_lower:
                    if file_path not in linked_files:
                        linked_files.append(file_path)

        # Prioritize CAD files over documentation
        if linked_files:
            cad_files = [
                f
                for f in linked_files
                if any(f.lower().endswith(ext) for ext in cad_extensions)
            ]
            if cad_files:
                return cad_files[:5]  # Limit to 5 CAD files
            # If no CAD files, return documentation files (limited)
            doc_files = [
                f
                for f in linked_files
                if any(f.lower().endswith(ext) for ext in doc_extensions)
            ]
            if doc_files:
                return doc_files[:3]  # Limit to 3 doc files

        return linked_files[:5]  # Overall limit

    def _matches_component(
        self, comp_name_lower: str, comp_words: List[str], target: str
    ) -> bool:
        """
        Check if component name matches target (directory or filename).

        Uses stricter matching:
        - Exact match (normalized)
        - Key word match (at least 2 significant words must match)
        - Avoids single-word matches that could be false positives

        Args:
            comp_name_lower: Lowercase component name
            comp_words: List of significant words from component name
            target: Target string (directory or filename) to match against

        Returns:
            True if component matches target
        """
        import re

        # Normalize target
        target_normalized = re.sub(r"[^a-z0-9]+", "-", target.lower())
        target_words = [
            w for w in re.split(r"[^a-z0-9]+", target_normalized) if len(w) > 2
        ]

        # Exact match (normalized)
        comp_normalized = re.sub(r"[^a-z0-9]+", "-", comp_name_lower)
        if comp_normalized == target_normalized:
            return True

        # Key word matching: require at least 2 significant words to match
        # This prevents false positives from single common words
        matches = 0
        for comp_word in comp_words:
            if len(comp_word) >= 4:  # Only match words of 4+ chars
                if comp_word in target_normalized or comp_word in target_words:
                    matches += 1

        # Require at least 2 matches for multi-word components, or 1 for short components
        if len(comp_words) > 1:
            return matches >= 2
        else:
            return matches >= 1 and len(comp_words[0]) >= 4

    def _generate_manufacturing_specs(
        self, fields_dict: Dict[str, Any], project_data: ProjectData
    ) -> Dict[str, Any]:
        """
        Generate manufacturing specs from available data.

        Extracts manufacturing information from manufacturing_processes,
        assembly documentation, and other sources.

        Args:
            fields_dict: Dictionary of generated fields
            project_data: Project data for extracting from docs

        Returns:
            ManufacturingSpec dictionary
        """
        processes = fields_dict.get("manufacturing_processes", [])

        # Identify joining processes (processes that join materials)
        joining_keywords = [
            "soldering",
            "welding",
            "gluing",
            "screwing",
            "bolting",
            "riveting",
            "adhesive",
        ]
        joining_processes = [
            p
            for p in processes
            if any(keyword in p.lower() for keyword in joining_keywords)
        ]

        # Convert processes to ProcessRequirement objects
        process_requirements = []
        for process in processes:
            # Extract tools for this process from tool_list
            required_tools = self._extract_tools_for_process(
                process, fields_dict.get("tool_list", [])
            )

            process_requirements.append(
                {
                    "process_name": process,
                    "parameters": {},
                    "validation_criteria": {},
                    "required_tools": required_tools,
                    "notes": "",
                }
            )

        # Extract quality standards (can be enhanced with NLP/LLM)
        quality_standards = []

        return {
            "joining_processes": joining_processes,
            "process_requirements": process_requirements,
            "quality_standards": quality_standards,
            "outer_dimensions": None,  # TODO: Extract from docs if available
            "notes": "",
        }

    def _extract_tools_for_process(
        self, process_name: str, tool_list: List[str]
    ) -> List[str]:
        """
        Extract relevant tools for a manufacturing process.

        Args:
            process_name: Name of the manufacturing process
            process_name_lower: Lowercase version of process name
            tool_list: List of available tools

        Returns:
            List of relevant tools
        """
        process_lower = process_name.lower()
        relevant_tools = []

        # Map processes to tool keywords
        tool_mappings = {
            "3d printing": ["3d printer", "printer"],
            "soldering": ["soldering iron", "solder", "iron"],
            "welding": ["welder", "welding"],
            "cutting": ["saw", "cutter", "knife"],
            "drilling": ["drill", "drill bit"],
            "assembly": ["screwdriver", "wrench", "pliers"],
        }

        # Find relevant tools
        for tool in tool_list:
            tool_lower = tool.lower()
            # Check if tool matches process keywords
            for proc_key, tool_keywords in tool_mappings.items():
                if proc_key in process_lower:
                    if any(keyword in tool_lower for keyword in tool_keywords):
                        if tool not in relevant_tools:
                            relevant_tools.append(tool)

        return relevant_tools

    def _get_bom_field(self, fields_dict: Dict[str, Any]) -> Any:
        """
        Get the BOM field, creating either a compressed summary or full BOM for manifest inclusion.

        Args:
            fields_dict: Dictionary of generated fields

        Returns:
            Full BOM dict if unified_bom_mode is True, compressed summary if False,
            otherwise URL string or empty string
        """
        # Check if we have a structured BOM from BOM normalization
        if "bom" in fields_dict:
            bom_value = fields_dict["bom"]
            # If it's a structured BOM (dict)
            if isinstance(bom_value, dict):
                if self.unified_bom_mode:
                    # Return full BOM in unified mode
                    return bom_value
                else:
                    # Return compressed summary in default mode
                    return self._create_compressed_bom_summary(bom_value)
            # If it's a string (URL), return it
            elif isinstance(bom_value, str):
                return bom_value

        # Fallback to empty string if no BOM field
        return ""

    def _create_compressed_bom_summary(
        self, full_bom: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a compressed BOM summary for manifest inclusion.

        Args:
            full_bom: Full BOM dictionary with all components

        Returns:
            Compressed BOM summary with statistics and external file reference
        """
        try:
            components = full_bom.get("components", [])

            # Calculate summary statistics
            total_components = len(components)
            total_quantity = sum(comp.get("quantity", 0) for comp in components)

            # Group components by category (based on name patterns)
            categories = self._categorize_components(components)

            # Calculate confidence statistics
            confidences = [
                comp.get("metadata", {}).get("confidence", 0) for comp in components
            ]
            avg_confidence = (
                round(sum(confidences) / len(confidences), 2) if confidences else 0
            )

            # Create compressed summary
            compressed_bom = {
                "id": full_bom.get("id"),
                "name": full_bom.get("name"),
                "summary": {
                    "total_components": total_components,
                    "total_quantity": total_quantity,
                    "categories": categories,
                    "average_confidence": avg_confidence,
                },
                "external_file": "bom/bom.json",  # Reference to external detailed BOM
                "metadata": {
                    "generated_at": full_bom.get("metadata", {}).get("generated_at"),
                    "generation_method": full_bom.get("metadata", {}).get(
                        "generation_method"
                    ),
                    "source_count": full_bom.get("metadata", {}).get("source_count"),
                },
            }

            return compressed_bom
        except Exception as e:
            # Fallback to simple summary if compression fails
            print(f"Warning: BOM compression failed: {e}")
            return {
                "id": full_bom.get("id", "unknown"),
                "name": full_bom.get("name", "Project BOM"),
                "summary": {
                    "total_components": 0,
                    "total_quantity": 0,
                    "categories": {},
                    "average_confidence": 0,
                },
                "external_file": "bom/bom.json",
                "metadata": {
                    "generated_at": full_bom.get("metadata", {}).get("generated_at"),
                    "generation_method": "fallback",
                    "source_count": 0,
                },
            }

    def _get_files_field(self) -> List[Dict[str, Any]]:
        """
        Get the files field with file inventory.

        Returns:
            List of file information dictionaries
        """
        files = []

        # Convert FileInfo objects to dictionaries
        for file_info in self.project_data.files:
            file_dict = {
                "path": file_info.path,
                "size": file_info.size,
                "type": file_info.file_type,
                "content_length": len(file_info.content) if file_info.content else 0,
            }
            files.append(file_dict)

        return files

    def _categorize_components(
        self, components: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Categorize components by type and count them.

        Args:
            components: List of component dictionaries

        Returns:
            Dictionary with category counts
        """
        categories = {}

        try:
            for comp in components:
                if not isinstance(comp, dict):
                    continue

                name = comp.get("name", "").lower()

                # Categorize based on name patterns
                if any(
                    keyword in name for keyword in ["screw", "bolt", "nut", "washer"]
                ):
                    category = "fasteners"
                elif any(
                    keyword in name
                    for keyword in ["resistor", "capacitor", "transistor", "ic", "chip"]
                ):
                    category = "electronics"
                elif any(keyword in name for keyword in ["motor", "actuator", "servo"]):
                    category = "mechanical"
                elif any(keyword in name for keyword in ["cable", "wire", "connector"]):
                    category = "electrical"
                elif any(keyword in name for keyword in ["sensor", "switch", "button"]):
                    category = "sensors"
                elif any(keyword in name for keyword in ["bearing", "gear", "pulley"]):
                    category = "mechanical_parts"
                else:
                    category = "other"

                categories[category] = categories.get(category, 0) + 1
        except Exception as e:
            print(f"Warning: Component categorization failed: {e}")
            categories = {"other": len(components) if components else 0}

        return categories


@dataclass
class LayerConfig:
    """
    Enhanced configuration for generation layers with validation and layer-specific settings.

    This dataclass provides configuration for all generation layers,
    including the new LLM layer. It supports both global settings and layer-specific
    configurations for fine-tuning the generation process.

    Attributes:
        use_direct: Enable direct field mapping layer
        use_heuristic: Enable heuristic pattern recognition layer
        use_nlp: Enable natural language processing layer
        use_llm: Enable large language model layer
        use_bom_normalization: Enable BOM normalization layer

        min_confidence: Minimum confidence threshold for field acceptance
        progressive_enhancement: Use progressive enhancement (stop when quality threshold met)
        save_reference: Save reference data for debugging/analysis

        direct_config: Configuration for direct layer
        heuristic_config: Configuration for heuristic layer
        nlp_config: Configuration for NLP layer
        llm_config: Configuration for LLM layer (provider, model, etc.)
    """

    # Core layer settings
    use_direct: bool = True
    use_heuristic: bool = True
    use_nlp: bool = True
    use_llm: bool = True  # Re-enable LLM layer - generation pipeline works fine
    use_bom_normalization: bool = False

    # Quality and processing settings
    min_confidence: float = 0.7
    progressive_enhancement: bool = True
    save_reference: bool = False

    # Layer-specific configurations
    direct_config: Dict[str, Any] = field(default_factory=dict)
    heuristic_config: Dict[str, Any] = field(default_factory=dict)
    nlp_config: Dict[str, Any] = field(default_factory=dict)
    llm_config: Dict[str, Any] = field(default_factory=dict)
    file_categorization_config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate_config()
        self._set_default_layer_configs()

    def _validate_config(self):
        """Validate configuration values"""
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError(
                f"min_confidence must be between 0.0 and 1.0, got {self.min_confidence}"
            )

        if not isinstance(self.use_direct, bool):
            raise ValueError(
                f"use_direct must be a boolean, got {type(self.use_direct)}"
            )

        if not isinstance(self.use_heuristic, bool):
            raise ValueError(
                f"use_heuristic must be a boolean, got {type(self.use_heuristic)}"
            )

        if not isinstance(self.use_nlp, bool):
            raise ValueError(f"use_nlp must be a boolean, got {type(self.use_nlp)}")

        if not isinstance(self.use_llm, bool):
            raise ValueError(f"use_llm must be a boolean, got {type(self.use_llm)}")

    def _set_default_layer_configs(self):
        """Set default layer-specific configurations, merging with provided configs"""
        # Define default configurations
        default_direct_config = {
            "extract_metadata": True,
            "fallback_to_defaults": True,
            "strict_validation": False,
        }
        default_heuristic_config = {
            "pattern_matching_enabled": True,
            "file_analysis_enabled": True,
            "content_analysis_enabled": True,
            "confidence_threshold": 0.6,
        }
        default_nlp_config = {
            "spacy_model": "en_core_web_sm",
            "max_text_length": 1000000,
            "entity_extraction": True,
            "semantic_analysis": True,
        }
        # Import provider selector to get default model
        from ..llm.provider_selection import get_provider_selector
        from ..llm.providers.base import LLMProviderType

        selector = get_provider_selector()
        default_model = selector.DEFAULT_MODELS.get(
            LLMProviderType.ANTHROPIC, "claude-sonnet-4-5-20250929"
        )

        default_llm_config = {
            "provider": "anthropic",  # openai, anthropic, local, etc.
            "model": default_model,
            "max_tokens": 1000,
            "temperature": 0.1,
            "timeout": 30,
            "api_key": None,  # Will be loaded from environment
            "base_url": None,  # For custom endpoints
            "max_retries": 3,
            "retry_delay": 1.0,
            "enable_caching": True,
            "cache_ttl": 3600,  # 1 hour
            "enable_streaming": False,
            "custom_headers": {},
            "fallback_to_nlp": True,  # Fallback to NLP if LLM fails
            "cost_tracking": True,
            "max_cost_per_request": 0.10,  # $0.10 max per request
            "prompt_templates": {
                "field_extraction": "Extract {field} from the following project information:",
                "content_analysis": "Analyze the following content and extract key information:",
                "quality_assessment": "Assess the quality and completeness of this manifest:",
            },
        }

        default_file_categorization_config = {
            "enable_llm_categorization": True,  # Enable Layer 2
            "analysis_depth": "shallow",  # Default depth (shallow/medium/deep)
            "fallback_to_heuristics": True,  # Fallback to Layer 1 when LLM unavailable
            "batch_size": 10,  # Files per LLM request
            "max_files_per_request": 50,  # Max files in single request
            "min_confidence_for_llm": 0.8,  # Skip LLM if Layer 1 confidence >= this (trust Layer 1 for clear patterns)
            "enable_caching": True,  # Enable caching by file content hash
        }

        # Merge with provided configs (provided configs take precedence)
        self.direct_config = {**default_direct_config, **self.direct_config}
        self.heuristic_config = {**default_heuristic_config, **self.heuristic_config}
        self.nlp_config = {**default_nlp_config, **self.nlp_config}
        self.llm_config = {**default_llm_config, **self.llm_config}
        self.file_categorization_config = {
            **default_file_categorization_config,
            **self.file_categorization_config,
        }

    def get_layer_config(self, layer_name: str) -> Dict[str, Any]:
        """Get configuration for a specific layer"""
        config_map = {
            "direct": self.direct_config,
            "heuristic": self.heuristic_config,
            "nlp": self.nlp_config,
            "llm": self.llm_config,
        }
        return config_map.get(layer_name, {})

    def set_layer_config(self, layer_name: str, config: Dict[str, Any]):
        """Set configuration for a specific layer"""
        if layer_name == "direct":
            self.direct_config.update(config)
        elif layer_name == "heuristic":
            self.heuristic_config.update(config)
        elif layer_name == "nlp":
            self.nlp_config.update(config)
        elif layer_name == "llm":
            self.llm_config.update(config)
        else:
            raise ValueError(f"Unknown layer: {layer_name}")

    def is_layer_enabled(self, layer_name: str) -> bool:
        """Check if a specific layer is enabled"""
        layer_map = {
            "direct": self.use_direct,
            "heuristic": self.use_heuristic,
            "nlp": self.use_nlp,
            "llm": self.use_llm,
        }
        return layer_map.get(layer_name, False)

    def get_llm_provider(self) -> str:
        """Get the configured LLM provider"""
        return self.llm_config.get("provider", "openai")

    def get_llm_model(self) -> str:
        """Get the configured LLM model"""
        return self.llm_config.get("model", "gpt-3.5-turbo")

    def get_llm_api_key(self) -> Optional[str]:
        """Get the LLM API key (from config or environment)"""
        api_key = self.llm_config.get("api_key")
        if api_key:
            return api_key

        # Try to load from environment
        import os

        provider = self.get_llm_provider()
        if provider == "openai":
            return os.getenv("OPENAI_API_KEY")
        elif provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        else:
            return os.getenv(f"{provider.upper()}_API_KEY")

    def is_llm_configured(self) -> bool:
        """Check if LLM layer is properly configured"""
        if not self.use_llm:
            return False

        api_key = self.get_llm_api_key()
        return api_key is not None and len(api_key.strip()) > 0

    def get_enabled_layers(self) -> List[GenerationLayer]:
        """Get list of enabled generation layers in processing order"""
        layers = []
        if self.use_direct:
            layers.append(GenerationLayer.DIRECT)
        if self.use_heuristic:
            layers.append(GenerationLayer.HEURISTIC)
        if self.use_nlp:
            layers.append(GenerationLayer.NLP)
        if self.use_llm and self.is_llm_configured():
            layers.append(GenerationLayer.LLM)
        if self.use_bom_normalization:
            layers.append(GenerationLayer.BOM_NORMALIZATION)
        return layers


@dataclass
class GenerationResult(Generic[T]):
    """
    Generic generation result wrapper with metadata.

    This dataclass provides a generic wrapper for generation results
    with associated metadata, processing logs, and quality information.
    It's used to wrap results from individual layers and the final
    manifest generation.

    Attributes:
        data: The actual generation result data (type T)
        metadata: Metadata about the generation process
    """

    data: T
    metadata: GenerationMetadata = field(default_factory=GenerationMetadata)

    def mark_as_reviewed(self) -> None:
        """
        Mark the generation as human-reviewed.

        Adds a flag to indicate that this result has been reviewed
        by a human and is ready for use.
        """
        if "REQUIRES_HUMAN_VERIFICATION" not in self.metadata.flags:
            self.metadata.flags.append("REQUIRES_HUMAN_VERIFICATION")

    def update_confidence(self, field: str, score: float) -> None:
        """
        Update confidence score for a specific field.

        Args:
            field: Name of the field
            score: Confidence score between 0.0 and 1.0
        """
        self.metadata.update_confidence(field, score)

    def add_processing_log(self, message: str) -> None:
        """
        Add a processing log entry.

        Args:
            message: Log message to add
        """
        self.metadata.add_processing_log(message)
