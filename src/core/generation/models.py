"""
Data models for OKH manifest generation system.

This module defines the core data structures used throughout the generation pipeline,
including enums, dataclasses, and result types.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
from typing import Dict, List, Optional, Any, Generic, TypeVar

# Generic type variables
T = TypeVar('T')


class PlatformType(Enum):
    """Supported platforms for manifest generation"""
    GITHUB = "github"
    GITLAB = "gitlab"
    CODEBERG = "codeberg"
    HACKADAY = "hackaday"
    UNKNOWN = "unknown"


class GenerationQuality(Enum):
    """Quality levels for generation results"""
    COMPLETE = auto()      # All critical elements generated
    PARTIAL = auto()       # Some critical elements missing
    INSUFFICIENT = auto()  # Majority of critical elements missing
    REQUIRES_REVIEW = auto()  # Significant ambiguities detected


class GenerationLayer(Enum):
    """Available generation layers"""
    DIRECT = "direct"      # Direct field mapping
    HEURISTIC = "heuristic"  # Rule-based pattern recognition
    NLP = "nlp"           # Natural language processing
    LLM = "llm"           # Large language model
    BOM_NORMALIZATION = "bom_normalization"  # BOM normalization and structuring
    USER_EDIT = "user_edit"  # User manual editing


@dataclass
class FileInfo:
    """Information about a project file"""
    path: str
    size: int
    content: str
    file_type: str


@dataclass
class DocumentInfo:
    """Information about project documentation"""
    title: str
    path: str
    doc_type: str
    content: str


@dataclass
class ProjectData:
    """Raw project data extracted from a platform"""
    platform: PlatformType
    url: str
    metadata: Dict[str, Any]
    files: List[FileInfo]
    documentation: List[DocumentInfo]
    raw_content: Dict[str, str]


@dataclass
class FieldGeneration:
    """Individual field generation result with metadata"""
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
        Get the files field with comprehensive file inventory.
        
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
    """Configuration for generation layers"""
    use_direct: bool = True
    use_heuristic: bool = True
    use_nlp: bool = True
    use_llm: bool = False
    use_bom_normalization: bool = False  # BOM normalization and structuring
    min_confidence: float = 0.7
    progressive_enhancement: bool = True
    save_reference: bool = False


@dataclass
class GenerationResult(Generic[T]):
    """Generic generation result wrapper"""
    data: T
    metadata: GenerationMetadata = field(default_factory=GenerationMetadata)
    
    def mark_as_reviewed(self) -> None:
        """Mark the generation as human-reviewed"""
        if "REQUIRES_HUMAN_VERIFICATION" not in self.metadata.flags:
            self.metadata.flags.append("REQUIRES_HUMAN_VERIFICATION")
    
    def update_confidence(self, field: str, score: float) -> None:
        """Update confidence score for a specific field"""
        self.metadata.update_confidence(field, score)
    
    def add_processing_log(self, message: str) -> None:
        """Add a processing log entry"""
        self.metadata.add_processing_log(message)
