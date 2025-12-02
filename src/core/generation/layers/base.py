"""
Base classes for generation layers.

This module defines the abstract base classes and interfaces that all
generation layers must implement, along with shared utilities for
file processing, text processing, and confidence calculation.

The base layer architecture provides:
- Standardized interfaces for all generation layers
- Shared utilities for common operations
- Consistent error handling and logging
- Configuration management
- Result processing and validation

All generation layers inherit from BaseGenerationLayer and must implement
the async process() method. The base class provides utilities
for file processing, text analysis, and confidence calculation.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from ..models import (
    FieldGeneration,
    FileInfo,
)
from ..models import GenerationLayer as LayerType
from ..models import (
    LayerConfig,
    ProjectData,
)
from ..utils import ConfidenceCalculator, FileProcessor, TextProcessor

# Configure logging
logger = logging.getLogger(__name__)


class LayerResult:
    """
    Result from a generation layer.

    This class encapsulates the results of processing by a single generation layer,
    including extracted fields, confidence scores, processing logs, and any errors
    that occurred during processing.

    Attributes:
        layer_type: The type of layer that produced this result
        fields: Dictionary of extracted fields with their generation metadata
        confidence_scores: Dictionary of confidence scores for each field
        processing_log: List of processing log messages
        errors: List of error messages encountered during processing
    """

    def __init__(self, layer_type: LayerType):
        """
        Initialize a layer result.

        Args:
            layer_type: The type of generation layer that produced this result
        """
        self.layer_type = layer_type
        self.fields: Dict[str, FieldGeneration] = {}
        self.confidence_scores: Dict[str, float] = {}
        self.processing_log: List[str] = []
        self.errors: List[str] = []

    def add_field(
        self,
        field_name: str,
        value: Any,
        confidence: float,
        generation_method: str,
        raw_source: str = "",
    ):
        """
        Add a generated field to the result.

        Args:
            field_name: Name of the field
            value: Extracted field value
            confidence: Confidence score between 0.0 and 1.0
            generation_method: Method used to extract the field
            raw_source: Raw source data used for extraction
        """
        # Validate confidence score
        if not 0.0 <= confidence <= 1.0:
            logger.warning(
                f"Invalid confidence score {confidence} for field {field_name}, clamping to [0.0, 1.0]"
            )
            confidence = max(0.0, min(1.0, confidence))

        self.fields[field_name] = FieldGeneration(
            value=value,
            confidence=confidence,
            source_layer=self.layer_type,
            generation_method=generation_method,
            raw_source=raw_source,
        )
        self.confidence_scores[field_name] = confidence

    def add_log(self, message: str):
        """
        Add a processing log message.

        Args:
            message: Log message to add
        """
        self.processing_log.append(message)
        logger.debug(f"[{self.layer_type.value}] {message}")

    def add_error(self, error: str):
        """
        Add an error message.

        Args:
            error: Error message to add
        """
        self.errors.append(error)
        logger.error(f"[{self.layer_type.value}] {error}")

    def get_field(self, field_name: str) -> Optional[FieldGeneration]:
        """
        Get a field by name.

        Args:
            field_name: Name of the field to retrieve

        Returns:
            FieldGeneration object or None if not found
        """
        return self.fields.get(field_name)

    def has_field(self, field_name: str) -> bool:
        """
        Check if a field exists.

        Args:
            field_name: Name of the field to check

        Returns:
            True if field exists, False otherwise
        """
        return field_name in self.fields

    def get_confidence(self, field_name: str) -> float:
        """
        Get confidence score for a field.

        Args:
            field_name: Name of the field

        Returns:
            Confidence score between 0.0 and 1.0, or 0.0 if field not found
        """
        return self.confidence_scores.get(field_name, 0.0)

    def get_field_count(self) -> int:
        """
        Get the number of fields in this result.

        Returns:
            Number of extracted fields
        """
        return len(self.fields)

    def get_average_confidence(self) -> float:
        """
        Get the average confidence score across all fields.

        Returns:
            Average confidence score, or 0.0 if no fields
        """
        if not self.confidence_scores:
            return 0.0
        return sum(self.confidence_scores.values()) / len(self.confidence_scores)

    def is_successful(self) -> bool:
        """
        Check if the layer processing was successful.

        Returns:
            True if no errors occurred, False otherwise
        """
        return len(self.errors) == 0


class BaseGenerationLayer(ABC):
    """
    Enhanced abstract base class for all generation layers with shared utilities.

    This abstract base class provides a standardized interface and shared utilities
    for all generation layers. It includes error handling, logging,
    configuration management, and common processing utilities.

    All generation layers must inherit from this class and implement the async
    process() method. The base class provides:
    - Shared utilities for file processing, text analysis, and confidence calculation
    - Configuration management and validation
    - Error handling and logging
    - Result processing and validation

    Attributes:
        layer_type: The type of generation layer
        layer_config: Configuration for this layer
        config: Layer-specific configuration dictionary
        _file_processor: Shared file processing utilities
        _text_processor: Shared text processing utilities
        _confidence_calculator: Shared confidence calculation utilities
    """

    def __init__(
        self, layer_type: LayerType, layer_config: Optional[LayerConfig] = None
    ):
        """
        Initialize the base generation layer.

        Args:
            layer_type: The type of generation layer
            layer_config: Configuration for this layer. If None, uses default configuration.

        Raises:
            ValueError: If layer_type is invalid
            RuntimeError: If initialization fails
        """
        if not isinstance(layer_type, LayerType):
            raise ValueError(f"Invalid layer type: {layer_type}")

        self.layer_type = layer_type
        self.layer_config = layer_config or LayerConfig()
        self.config: Dict[str, Any] = {}

        try:
            # Initialize shared utilities
            self._file_processor = FileProcessor()
            self._text_processor = TextProcessor()
            self._confidence_calculator = ConfidenceCalculator()

            # Load layer-specific configuration
            self._load_layer_specific_config()

            logger.debug(f"Initialized {layer_type.value} layer")

        except Exception as e:
            logger.error(f"Failed to initialize {layer_type.value} layer: {e}")
            raise RuntimeError(f"Layer initialization failed: {e}")

    @abstractmethod
    async def process(self, project_data: ProjectData) -> LayerResult:
        """
        Process project data and extract fields.

        This is the main processing method that all generation layers must implement.
        It should analyze the provided project data and extract relevant fields
        for the OKH manifest.

        Args:
            project_data: Raw project data from platform extractor

        Returns:
            LayerResult containing extracted fields and metadata

        Raises:
            ValueError: If project_data is invalid
            RuntimeError: If processing fails due to system errors
        """
        pass

    def _load_layer_specific_config(self):
        """Load layer-specific configuration from LayerConfig"""
        layer_name = self.layer_type.value
        layer_specific_config = self.layer_config.get_layer_config(layer_name)
        self.config.update(layer_specific_config)

    def set_config(self, config: Dict[str, Any]):
        """Set layer configuration"""
        # Make a deep copy to prevent external modifications
        import copy

        self.config = copy.deepcopy(config)

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)

    def update_config(self, config: Dict[str, Any]):
        """Update layer configuration with new values"""
        import copy

        self.config.update(copy.deepcopy(config))

    def get_layer_config(self) -> LayerConfig:
        """Get the LayerConfig instance"""
        return self.layer_config

    def is_enabled(self) -> bool:
        """Check if this layer is enabled in the LayerConfig"""
        return self.layer_config.is_layer_enabled(self.layer_type.value)

    # Shared utility methods for file processing
    def detect_file_type(self, file_path: str) -> str:
        """Detect file type based on extension"""
        return self._file_processor.detect_file_type(file_path)

    def extract_file_content(self, file_info: FileInfo) -> Optional[str]:
        """Extract content from a file if it's a text file"""
        return self._file_processor.extract_file_content(file_info)

    def find_files_by_pattern(
        self, files: List[FileInfo], pattern: str
    ) -> List[FileInfo]:
        """Find files matching a regex pattern"""
        return self._file_processor.find_files_by_pattern(files, pattern)

    def find_files_by_extension(
        self, files: List[FileInfo], extensions: List[str]
    ) -> List[FileInfo]:
        """Find files with specific extensions"""
        return self._file_processor.find_files_by_extension(files, extensions)

    def categorize_files(self, files: List[FileInfo]) -> Dict[str, List[FileInfo]]:
        """Categorize files by type"""
        return self._file_processor.categorize_files(files)

    def match_file_patterns(self, files: List[FileInfo]) -> Dict[str, List[tuple]]:
        """Match files against predefined patterns"""
        return self._file_processor.match_file_patterns(files)

    def filter_excluded_files(self, files: List[FileInfo]) -> List[FileInfo]:
        """Filter out files in excluded directories"""
        return self._file_processor.filter_excluded_files(files)

    def is_text_file(self, file_path: str) -> bool:
        """Check if a file is likely to contain text"""
        return self._file_processor.is_text_file(file_path)

    def is_image_file(self, file_path: str) -> bool:
        """Check if a file is an image"""
        return self._file_processor.is_image_file(file_path)

    def is_design_file(self, file_path: str) -> bool:
        """Check if a file is a design file"""
        return self._file_processor.is_design_file(file_path)

    # Shared utility methods for text processing
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        return self._text_processor.clean_text(text)

    def extract_license_type(self, content: str) -> Optional[str]:
        """Extract license type from content"""
        return self._text_processor.extract_license_type(content)

    def extract_version_from_text(self, text: str) -> Optional[str]:
        """Extract version information from text"""
        return self._text_processor.extract_version_from_text(text)

    def extract_manufacturing_processes(self, text: str) -> List[str]:
        """Extract manufacturing processes from text"""
        return self._text_processor.extract_manufacturing_processes(text)

    def classify_content_type(self, text: str):
        """Classify the type of content"""
        return self._text_processor.classify_content_type(text)

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text"""
        return self._text_processor.extract_keywords(text, max_keywords)

    def extract_measurements(self, text: str) -> List[Dict[str, str]]:
        """Extract measurements and dimensions from text"""
        return self._text_processor.extract_measurements(text)

    def is_technical_content(self, text: str) -> bool:
        """Determine if text contains technical content"""
        return self._text_processor.is_technical_content(text)

    # Shared utility methods for confidence calculation
    def calculate_confidence(
        self,
        field: str,
        value: Any,
        source: str,
        content_quality: Optional[Dict[str, Any]] = None,
    ) -> float:
        """Calculate confidence score for a field extraction"""
        return self._confidence_calculator.calculate_field_confidence(
            field, value, source, content_quality
        )

    def calculate_layer_confidence(self, confidence_scores: Dict[str, float]) -> float:
        """Calculate overall confidence for a layer"""
        return self._confidence_calculator.calculate_layer_confidence(confidence_scores)

    def get_confidence_level(self, confidence: float):
        """Get confidence level category for a score"""
        return self._confidence_calculator.get_confidence_level(confidence)

    def validate_confidence_score(self, confidence: float) -> bool:
        """Validate that a confidence score is within valid range"""
        return self._confidence_calculator.validate_confidence_score(confidence)

    def normalize_confidence_scores(
        self, confidence_scores: Dict[str, float]
    ) -> Dict[str, float]:
        """Normalize confidence scores to ensure they're within valid range"""
        return self._confidence_calculator.normalize_confidence_scores(
            confidence_scores
        )

    # Convenience methods for common operations
    def find_license_files(self, files: List[FileInfo]) -> List[FileInfo]:
        """Find license files in the project"""
        return self.find_files_by_pattern(
            files, r"(?i)^(license|licence|copying)(\.(txt|md))?$"
        )

    def find_readme_files(self, files: List[FileInfo]) -> List[FileInfo]:
        """Find README files in the project, prioritizing the most important one"""
        # Find all README files
        all_readme_files = self.find_files_by_pattern(
            files, r"(?i)readme(\.(md|rst|txt))?$"
        )

        if not all_readme_files:
            return []

        # Prioritize README files by importance
        # 1. Root README.md (highest priority)
        # 2. docs/README.md (second priority - often contains main project description)
        # 3. Other README files

        root_readme = [f for f in all_readme_files if f.path.lower() == "readme.md"]
        docs_readme = [
            f for f in all_readme_files if f.path.lower() == "docs/readme.md"
        ]
        other_readme = [
            f
            for f in all_readme_files
            if f.path.lower() not in ["readme.md", "docs/readme.md"]
        ]

        # Return in priority order
        return root_readme + docs_readme + other_readme

    def find_bom_files(self, files: List[FileInfo]) -> List[FileInfo]:
        """Find BOM files in the project"""
        return self.find_files_by_pattern(
            files, r"(?i)^(bom|bill.of.materials|materials)(\.(txt|md|csv|json))?$"
        )

    def get_text_files(self, files: List[FileInfo]) -> List[FileInfo]:
        """Get all text files from the project"""
        return [f for f in files if self.is_text_file(f.path)]

    def get_image_files(self, files: List[FileInfo]) -> List[FileInfo]:
        """Get all image files from the project"""
        return [f for f in files if self.is_image_file(f.path)]

    def get_design_files(self, files: List[FileInfo]) -> List[FileInfo]:
        """Get all design files from the project"""
        return [f for f in files if self.is_design_file(f.path)]

    def validate_project_data(self, project_data: ProjectData) -> bool:
        """
        Validate project data for processing.

        Args:
            project_data: Project data to validate

        Returns:
            True if valid, False otherwise
        """
        if not project_data:
            logger.error("Project data is None")
            return False

        if not isinstance(project_data, ProjectData):
            logger.error(f"Invalid project data type: {type(project_data)}")
            return False

        if not project_data.files and not project_data.documentation:
            logger.warning("Project data has no files or documentation")
            return False

        return True

    def create_layer_result(self) -> LayerResult:
        """
        Create a new LayerResult instance for this layer.

        Returns:
            New LayerResult instance
        """
        return LayerResult(self.layer_type)

    def log_processing_start(self, project_data: ProjectData):
        """
        Log the start of processing.

        Args:
            project_data: Project data being processed
        """
        logger.info(
            f"Starting {self.layer_type.value} layer processing for: {project_data.url}"
        )

    def log_processing_end(self, result: LayerResult):
        """
        Log the end of processing.

        Args:
            result: Processing result
        """
        field_count = result.get_field_count()
        avg_confidence = result.get_average_confidence()
        logger.info(
            f"Completed {self.layer_type.value} layer processing: {field_count} fields, avg confidence: {avg_confidence:.2f}"
        )

    def handle_processing_error(self, error: Exception, result: LayerResult) -> None:
        """
        Handle processing errors consistently.

        Args:
            error: Exception that occurred
            result: LayerResult to add error to
        """
        error_msg = f"Processing error in {self.layer_type.value} layer: {str(error)}"
        result.add_error(error_msg)
        logger.error(error_msg, exc_info=True)
