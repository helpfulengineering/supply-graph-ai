from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
from typing import Dict, List, Optional, Any, Generic, TypeVar
from .base_types import NormalizedRequirements, NormalizedCapabilities

# Generic type variables
T = TypeVar('T')

class ExtractionQuality(Enum):
    """Detailed quality assessment of extraction"""
    COMPLETE = auto()      # All critical elements extracted
    PARTIAL = auto()       # Some critical elements missing
    INSUFFICIENT = auto()  # Majority of critical elements missing
    REQUIRES_REVIEW = auto()  # Significant ambiguities detected

class ExtractionFlag(Enum):
    """Flags to indicate specific extraction characteristics or issues"""
    AMBIGUOUS_CONTENT = auto()
    POTENTIAL_STANDARD_DEVIATION = auto()
    MISSING_CRITICAL_FIELD = auto()
    REQUIRES_HUMAN_VERIFICATION = auto()

@dataclass
class ExtractionMetadata:
    """Comprehensive metadata about the extraction process"""
    extraction_timestamp: datetime = field(default_factory=datetime.now)
    source_document: Optional[str] = None
    extraction_quality: ExtractionQuality = ExtractionQuality.INSUFFICIENT
    flags: List[ExtractionFlag] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    processing_logs: List[str] = field(default_factory=list)

@dataclass
class ExtractionResult(Generic[T]):
    """Comprehensive extraction result"""
    data: T  # Extracted data object
    metadata: ExtractionMetadata = field(default_factory=ExtractionMetadata)
    
    def mark_as_reviewed(self) -> None:
        """Mark the extraction as human-reviewed"""
        if ExtractionFlag.REQUIRES_HUMAN_VERIFICATION not in self.metadata.flags:
            self.metadata.flags.append(ExtractionFlag.REQUIRES_HUMAN_VERIFICATION)
    
    def update_confidence(self, field: str, score: float) -> None:
        """Update confidence score for a specific field"""
        self.metadata.confidence_scores[field] = max(0.0, min(1.0, score))
    
    def add_processing_log(self, message: str) -> None:
        """Add a processing log entry"""
        self.metadata.processing_logs.append(message)

class BaseExtractor(ABC):
    """Base class for all extractors"""
    
    def __init__(self):
        self._preprocessors = []
    
    def add_preprocessor(self, preprocessor):
        """Add preprocessing step before extraction"""
        self._preprocessors.append(preprocessor)
    
    def extract_requirements(self, content: Dict[str, Any]) -> ExtractionResult[NormalizedRequirements]:
        """Extract and normalize requirements data"""
        # Apply preprocessors
        processed_data = content
        for preprocessor in self._preprocessors:
            processed_data = preprocessor(processed_data)
        
        # Multi-stage extraction
        initial_data = self._initial_parse_requirements(processed_data)
        extracted_data = self._detailed_extract_requirements(initial_data)
        final_data = self._validate_and_refine_requirements(extracted_data)
        
        # Create result
        result = ExtractionResult(data=final_data)
        self._assess_extraction_quality(result, "requirements")
        
        return result
    
    def extract_capabilities(self, content: Dict[str, Any]) -> ExtractionResult[NormalizedCapabilities]:
        """Extract and normalize capabilities data"""
        # Apply preprocessors
        processed_data = content
        for preprocessor in self._preprocessors:
            processed_data = preprocessor(processed_data)
        
        # Multi-stage extraction
        initial_data = self._initial_parse_capabilities(processed_data)
        extracted_data = self._detailed_extract_capabilities(initial_data)
        final_data = self._validate_and_refine_capabilities(extracted_data)
        
        # Create result
        result = ExtractionResult(data=final_data)
        self._assess_extraction_quality(result, "capabilities")
        
        return result
    
    @abstractmethod
    def _initial_parse_requirements(self, content: Dict[str, Any]) -> Any:
        """Initial parsing of requirements data"""
        pass
    
    @abstractmethod
    def _detailed_extract_requirements(self, parsed_data: Any) -> NormalizedRequirements:
        """Detailed extraction of requirements data"""
        pass
    
    def _validate_and_refine_requirements(self, extracted_data: NormalizedRequirements) -> NormalizedRequirements:
        """Validate and refine extracted requirements data"""
        return extracted_data
    
    @abstractmethod
    def _initial_parse_capabilities(self, content: Dict[str, Any]) -> Any:
        """Initial parsing of capabilities data"""
        pass
    
    @abstractmethod
    def _detailed_extract_capabilities(self, parsed_data: Any) -> NormalizedCapabilities:
        """Detailed extraction of capabilities data"""
        pass
    
    def _validate_and_refine_capabilities(self, extracted_data: NormalizedCapabilities) -> NormalizedCapabilities:
        """Validate and refine extracted capabilities data"""
        return extracted_data
    
    def _assess_extraction_quality(self, extraction_result: ExtractionResult, extraction_type: str) -> None:
        """Assess the overall quality of the extraction"""
        critical_fields = self._get_critical_fields(extraction_type)
        confidence_scores = extraction_result.metadata.confidence_scores
        
        low_confidence_fields = [
            field for field, score in confidence_scores.items()
            if score < 0.7 and field in critical_fields
        ]
        
        if not low_confidence_fields:
            extraction_result.metadata.extraction_quality = ExtractionQuality.COMPLETE
        elif len(low_confidence_fields) < len(critical_fields) / 2:
            extraction_result.metadata.extraction_quality = ExtractionQuality.PARTIAL
            extraction_result.metadata.flags.append(ExtractionFlag.MISSING_CRITICAL_FIELD)
        else:
            extraction_result.metadata.extraction_quality = ExtractionQuality.INSUFFICIENT
            extraction_result.metadata.flags.append(ExtractionFlag.REQUIRES_HUMAN_VERIFICATION)
    
    def _get_critical_fields(self, extraction_type: str) -> List[str]:
        """Define critical fields for quality assessment"""
        return []

