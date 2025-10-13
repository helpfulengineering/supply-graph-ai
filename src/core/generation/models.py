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
            "quality_report": quality_dict,
            "confidence_scores": self.confidence_scores,
            "missing_fields": self.missing_fields
        }


@dataclass
class LayerConfig:
    """Configuration for generation layers"""
    use_direct: bool = True
    use_heuristic: bool = True
    use_nlp: bool = True
    use_llm: bool = False
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
