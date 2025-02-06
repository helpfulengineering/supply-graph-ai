from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
from typing import (
    Any, Dict, List, Optional, 
    Generic, TypeVar, Union, Type
)

# Generic type variables for requirements and capabilities
R = TypeVar('R')
C = TypeVar('C')
I = TypeVar('I')  # Input type
E = TypeVar('E')  # Extracted type

class ProcessingStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    PARTIALLY_COMPLETED = auto()
    FULLY_COMPLETED = auto()
    NO_RESULT = auto()
    ERROR = auto()

class ExtractionQuality(Enum):
    """
    Detailed quality assessment of extraction
    Provides nuanced understanding of extraction completeness and reliability
    """
    COMPLETE = auto()      # All critical elements extracted
    PARTIAL = auto()       # Some critical elements missing
    INSUFFICIENT = auto()  # Majority of critical elements missing
    REQUIRES_REVIEW = auto()  # Significant ambiguities detected

class ExtractionFlag(Enum):
    """
    Flags to indicate specific extraction characteristics or issues
    """
    AMBIGUOUS_CONTENT = auto()
    POTENTIAL_STANDARD_DEVIATION = auto()
    MISSING_CRITICAL_FIELD = auto()
    REQUIRES_HUMAN_VERIFICATION = auto()


@dataclass
class ExtractionConfig:
    """
    Configuration for extraction modules
    
    Allows flexible, extensible configuration of extraction parameters
    """
    name: str
    type: str
    domain: str
    priority: int = 100
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExtractionMetadata:
    """
    Comprehensive metadata about the extraction process
    """
    extraction_timestamp: datetime = field(default_factory=datetime.now)
    source_document: Optional[str] = None
    extraction_quality: ExtractionQuality = ExtractionQuality.INSUFFICIENT
    flags: List[ExtractionFlag] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    processing_logs: List[str] = field(default_factory=list)

@dataclass
class ExtractionResult(Generic[T]):
    """
    Comprehensive extraction result
    
    Provides a structured, informative output from the extraction process
    """
    data: T  # Extracted data object
    metadata: ExtractionMetadata = field(default_factory=ExtractionMetadata)
    
    def mark_as_reviewed(self) -> None:
        """
        Mark the extraction as human-reviewed
        """
        self.metadata.flags.append(
            ExtractionFlag.REQUIRES_HUMAN_VERIFICATION
        )
    
    def update_confidence(self, field: str, score: float) -> None:
        """
        Update confidence score for a specific field
        
        Args:
            field: Name of the field to update
            score: Confidence score (0.0 to 1.0)
        """
        self.metadata.confidence_scores[field] = max(0.0, min(1.0, score))
    
    def add_processing_log(self, message: str) -> None:
        """
        Add a processing log entry
        
        Args:
            message: Log message describing extraction process
        """
        self.metadata.processing_logs.append(message)


class BaseExtractor(Generic[T]):
    """
    Advanced extraction framework with sophisticated handling
    
    Supports multi-stage extraction with comprehensive output
    """

    def __init__(self, validation_context: Optional[ValidationContext] = None):
        self.validation_context = validation_context or DefaultValidationContext()
        self._preprocessors: List[Callable] = []
    
    def add_preprocessor(self, preprocessor: Callable) -> None:
        """Add preprocessing step before extraction"""
        self._preprocessors.append(preprocessor)
    
    def extract(self, input_data: Any) -> ExtractionResult[T]:
        """Enhanced extraction with preprocessing and validation"""
        # Apply preprocessors
        processed_data = input_data
        for preprocessor in self._preprocessors:
            processed_data = preprocessor(processed_data)

    def reset(self) -> None:
        """
        Reset the extractor to its initial state
        """
        # Clear any internal state
        pass
    
    def extract(self, input_data: Any) -> ExtractionResult[T]:
        """
        Primary extraction method
        
        Args:
            input_data: Source data to extract information from
        
        Returns:
            Comprehensive extraction result
        """
        # Stage 1: Initial Parsing
        initial_data = self._initial_parse(input_data)
        
        # Stage 2: Detailed Extraction
        extracted_data = self._detailed_extract(initial_data)
        
        # Stage 3: Validation and Refinement
        final_data = self._validate_and_refine(extracted_data)
        
        # Construct extraction result
        result = ExtractionResult[T](data=final_data)
        
        # Assess extraction quality
        self._assess_extraction_quality(result)
        
        return result
    
    def _initial_parse(self, input_data: Any) -> Any:
        """
        Initial parsing stage
        Converts input to a standardized intermediate format
        
        Args:
            input_data: Raw input data
        
        Returns:
            Parsed intermediate representation
        """
        raise NotImplementedError("Subclasses must implement initial parsing")
    
    def _detailed_extract(self, parsed_data: Any) -> T:
        """
        Detailed extraction stage
        Extracts specific domain-relevant information
        
        Args:
            parsed_data: Intermediate parsed representation
        
        Returns:
            Extracted data object
        """
        raise NotImplementedError("Subclasses must implement detailed extraction")
    
    def _validate_and_refine(self, extracted_data: T) -> T:
        """
        Validation and refinement stage
        Performs cross-referencing and potential corrections
        
        Args:
            extracted_data: Initially extracted data
        
        Returns:
            Validated and potentially refined data
        """
        return extracted_data
    
    def _assess_extraction_quality(
        self, 
        extraction_result: ExtractionResult[T]
    ) -> None:
        """
        Assess the overall quality of the extraction
        
        Args:
            extraction_result: Result of the extraction process
        """
        # Default implementation provides basic quality assessment
        # Subclasses should override with domain-specific logic
        
        # Example basic implementation
        critical_fields = self._get_critical_fields()
        confidence_scores = extraction_result.metadata.confidence_scores
        
        low_confidence_fields = [
            field for field, score in confidence_scores.items()
            if score < 0.7 and field in critical_fields
        ]
        
        if not low_confidence_fields:
            extraction_result.metadata.extraction_quality = ExtractionQuality.COMPLETE
        elif len(low_confidence_fields) < len(critical_fields) / 2:
            extraction_result.metadata.extraction_quality = ExtractionQuality.PARTIAL
            extraction_result.metadata.flags.append(
                ExtractionFlag.MISSING_CRITICAL_FIELD
            )
        else:
            extraction_result.metadata.extraction_quality = ExtractionQuality.INSUFFICIENT
            extraction_result.metadata.flags.append(
                ExtractionFlag.REQUIRES_HUMAN_VERIFICATION
            )
    
    def _get_critical_fields(self) -> List[str]:
        """
        Define critical fields for quality assessment
        
        Returns:
            List of critical field names
        """
        return []


