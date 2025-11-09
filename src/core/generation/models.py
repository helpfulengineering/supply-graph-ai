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
from enum import Enum, auto
from datetime import datetime
from typing import Dict, List, Optional, Any, Generic, TypeVar, Union, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ...models.okh import DocumentationType

# Generic type variables
T = TypeVar('T')


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
    COMPLETE = auto()      # All critical elements generated
    PARTIAL = auto()       # Some critical elements missing
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
    MEDIUM = "medium"    # First 2000 chars, structure analysis
    DEEP = "deep"        # Full document, semantic analysis


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
    DIRECT = "direct"      # Direct field mapping
    HEURISTIC = "heuristic"  # Rule-based pattern recognition
    NLP = "nlp"           # Natural language processing
    LLM = "llm"           # Large language model
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
    destination_type: 'DocumentationType'  # Forward reference
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
        destination_type: 'DocumentationType',
        destination_path: str,
        confidence: float = 0.0
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
            confidence=confidence
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
    
    def get_routes_by_type(self, destination_type: 'DocumentationType') -> Dict[str, RouteEntry]:
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
            "recommendations": self.quality_report.recommendations
        }
        
        return {
            "title": fields_dict.get("title", "Unknown"),
            "version": fields_dict.get("version", "1.0.0"),
            "repo": fields_dict.get("repo", ""),
            "license": fields_dict.get("license", ""),
            "description": fields_dict.get("description", ""),
            "confidence_scores": self.confidence_scores,
            "missing_fields": self.missing_fields
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
            "license": fields_dict.get("license", ""),
            "description": fields_dict.get("description", ""),
            "function": fields_dict.get("function", ""),
            "intended_use": fields_dict.get("intended_use", ""),
            "keywords": fields_dict.get("keywords", []),
            "contact": fields_dict.get("contact", {}),
            "organization": fields_dict.get("organization", {}),
            "development_stage": fields_dict.get("development_stage", "development"),
            "technology_readiness_level": fields_dict.get("technology_readiness_level", "TRL-1"),
            "manufacturing_files": fields_dict.get("manufacturing_files", []),
            "design_files": fields_dict.get("design_files", []),
            "making_instructions": fields_dict.get("making_instructions", []),
            "operating_instructions": fields_dict.get("operating_instructions", []),
            "technical_specifications": fields_dict.get("technical_specifications", []),
            "publications": fields_dict.get("publications", []),
            "tool_list": fields_dict.get("tool_list", []),
            "manufacturing_processes": fields_dict.get("manufacturing_processes", []),
            "materials": fields_dict.get("materials", []),
            "manufacturing_specs": fields_dict.get("manufacturing_specs", {}),
            "bom": self._get_bom_field(fields_dict),
            "standards_used": fields_dict.get("standards_used", []),
            "tsdc": fields_dict.get("tsdc", []),
            "parts": fields_dict.get("parts", []),
            "sub_parts": fields_dict.get("sub_parts", []),
            "software": fields_dict.get("software", []),
            "files": self._get_files_field(),
            "metadata": {
                "generated_at": datetime.now().isoformat() + "Z",
                "generation_confidence": round(self.quality_report.overall_quality, 2),
                "missing_required_fields": self.missing_fields,
                "generation_method": "automated_extraction"
            }
        }
        
        # Add optional fields if they exist
        optional_fields = [
            "licensor", "documentation_language", "contact", "organization"
        ]
        for field in optional_fields:
            if field in fields_dict and fields_dict[field]:
                manifest[field] = fields_dict[field]
        
        # Ensure required fields are present with defaults
        if "licensor" not in manifest or not manifest["licensor"]:
            # Try to extract licensor from organization or repo URL
            org = fields_dict.get("organization", {})
            if isinstance(org, dict) and org.get("name"):
                manifest["licensor"] = org["name"]
            elif fields_dict.get("repo"):
                # Extract organization from repo URL (e.g., "nasa-jpl" from "https://github.com/nasa-jpl/open-source-rover")
                repo_url = fields_dict["repo"]
                if "github.com/" in repo_url:
                    parts = repo_url.split("github.com/")[-1].split("/")
                    if len(parts) >= 1:
                        manifest["licensor"] = parts[0]
                else:
                    manifest["licensor"] = "Unknown"
            else:
                manifest["licensor"] = "Unknown"
        
        if "documentation_language" not in manifest or not manifest["documentation_language"]:
            manifest["documentation_language"] = "en"  # Default to English
        
        return manifest
    
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
    
    def _create_compressed_bom_summary(self, full_bom: Dict[str, Any]) -> Dict[str, Any]:
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
            confidences = [comp.get("metadata", {}).get("confidence", 0) for comp in components]
            avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0
            
            # Create compressed summary
            compressed_bom = {
                "id": full_bom.get("id"),
                "name": full_bom.get("name"),
                "summary": {
                    "total_components": total_components,
                    "total_quantity": total_quantity,
                    "categories": categories,
                    "average_confidence": avg_confidence
                },
                "external_file": "bom/bom.json",  # Reference to external detailed BOM
                "metadata": {
                    "generated_at": full_bom.get("metadata", {}).get("generated_at"),
                    "generation_method": full_bom.get("metadata", {}).get("generation_method"),
                    "source_count": full_bom.get("metadata", {}).get("source_count")
                }
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
                    "average_confidence": 0
                },
                "external_file": "bom/bom.json",
                "metadata": {
                    "generated_at": full_bom.get("metadata", {}).get("generated_at"),
                    "generation_method": "fallback",
                    "source_count": 0
                }
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
                "content_length": len(file_info.content) if file_info.content else 0
            }
            files.append(file_dict)
        
        return files
    
    def _categorize_components(self, components: List[Dict[str, Any]]) -> Dict[str, int]:
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
                if any(keyword in name for keyword in ["screw", "bolt", "nut", "washer"]):
                    category = "fasteners"
                elif any(keyword in name for keyword in ["resistor", "capacitor", "transistor", "ic", "chip"]):
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
            raise ValueError(f"min_confidence must be between 0.0 and 1.0, got {self.min_confidence}")
        
        if not isinstance(self.use_direct, bool):
            raise ValueError(f"use_direct must be a boolean, got {type(self.use_direct)}")
        
        if not isinstance(self.use_heuristic, bool):
            raise ValueError(f"use_heuristic must be a boolean, got {type(self.use_heuristic)}")
        
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
            "strict_validation": False
        }
        default_heuristic_config = {
            "pattern_matching_enabled": True,
            "file_analysis_enabled": True,
            "content_analysis_enabled": True,
            "confidence_threshold": 0.6
        }
        default_nlp_config = {
            "spacy_model": "en_core_web_sm",
            "max_text_length": 1000000,
            "entity_extraction": True,
            "semantic_analysis": True
        }
        # Import provider selector to get default model
        from ..llm.provider_selection import get_provider_selector
        from ..llm.providers.base import LLMProviderType
        selector = get_provider_selector()
        default_model = selector.DEFAULT_MODELS.get(LLMProviderType.ANTHROPIC, "claude-sonnet-4-5-20250929")
        
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
                "quality_assessment": "Assess the quality and completeness of this manifest:"
            }
        }
        
        default_file_categorization_config = {
            "enable_llm_categorization": True,  # Enable Layer 2
            "analysis_depth": "shallow",        # Default depth (shallow/medium/deep)
            "fallback_to_heuristics": True,     # Fallback to Layer 1 when LLM unavailable
            "batch_size": 10,                   # Files per LLM request
            "max_files_per_request": 50,        # Max files in single request
            "min_confidence_for_llm": 0.5,      # Only use LLM if Layer 1 confidence < this
            "enable_caching": True,             # Enable caching by file content hash
        }
        
        # Merge with provided configs (provided configs take precedence)
        self.direct_config = {**default_direct_config, **self.direct_config}
        self.heuristic_config = {**default_heuristic_config, **self.heuristic_config}
        self.nlp_config = {**default_nlp_config, **self.nlp_config}
        self.llm_config = {**default_llm_config, **self.llm_config}
        self.file_categorization_config = {**default_file_categorization_config, **self.file_categorization_config}
    
    def get_layer_config(self, layer_name: str) -> Dict[str, Any]:
        """Get configuration for a specific layer"""
        config_map = {
            "direct": self.direct_config,
            "heuristic": self.heuristic_config,
            "nlp": self.nlp_config,
            "llm": self.llm_config
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
            "llm": self.use_llm
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
