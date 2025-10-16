"""
Base classes for generation layers.

This module defines the abstract base classes and interfaces that all
generation layers must implement, along with shared utilities for
file processing, text processing, and confidence calculation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from enum import Enum

from ..models import ProjectData, FieldGeneration, GenerationLayer as LayerType, FileInfo, LayerConfig
from ..utils import FileProcessor, TextProcessor, ConfidenceCalculator


class LayerResult:
    """Result from a generation layer"""
    
    def __init__(self, layer_type: LayerType):
        self.layer_type = layer_type
        self.fields: Dict[str, FieldGeneration] = {}
        self.confidence_scores: Dict[str, float] = {}
        self.processing_log: List[str] = []
        self.errors: List[str] = []
    
    def add_field(self, field_name: str, value: Any, confidence: float, 
                  generation_method: str, raw_source: str = ""):
        """Add a generated field to the result"""
        self.fields[field_name] = FieldGeneration(
            value=value,
            confidence=confidence,
            source_layer=self.layer_type,
            generation_method=generation_method,
            raw_source=raw_source
        )
        self.confidence_scores[field_name] = confidence
    
    def add_log(self, message: str):
        """Add a processing log message"""
        self.processing_log.append(message)
    
    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(error)
    
    def get_field(self, field_name: str) -> Optional[FieldGeneration]:
        """Get a field by name"""
        return self.fields.get(field_name)
    
    def has_field(self, field_name: str) -> bool:
        """Check if a field exists"""
        return field_name in self.fields
    
    def get_confidence(self, field_name: str) -> float:
        """Get confidence score for a field"""
        return self.confidence_scores.get(field_name, 0.0)


class BaseGenerationLayer(ABC):
    """Enhanced abstract base class for all generation layers with shared utilities"""
    
    def __init__(self, layer_type: LayerType, layer_config: Optional[LayerConfig] = None):
        self.layer_type = layer_type
        self.layer_config = layer_config or LayerConfig()
        self.config: Dict[str, Any] = {}
        
        # Initialize shared utilities
        self._file_processor = FileProcessor()
        self._text_processor = TextProcessor()
        self._confidence_calculator = ConfidenceCalculator()
        
        # Load layer-specific configuration
        self._load_layer_specific_config()
    
    @abstractmethod
    async def process(self, project_data: ProjectData) -> LayerResult:
        """
        Process project data and extract fields.
        
        Args:
            project_data: Raw project data from platform extractor
            
        Returns:
            LayerResult containing extracted fields and metadata
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
    
    def find_files_by_pattern(self, files: List[FileInfo], pattern: str) -> List[FileInfo]:
        """Find files matching a regex pattern"""
        return self._file_processor.find_files_by_pattern(files, pattern)
    
    def find_files_by_extension(self, files: List[FileInfo], extensions: List[str]) -> List[FileInfo]:
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
    def calculate_confidence(self, field: str, value: Any, source: str, 
                           content_quality: Optional[Dict[str, Any]] = None) -> float:
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
    
    def normalize_confidence_scores(self, confidence_scores: Dict[str, float]) -> Dict[str, float]:
        """Normalize confidence scores to ensure they're within valid range"""
        return self._confidence_calculator.normalize_confidence_scores(confidence_scores)
    
    # Convenience methods for common operations
    def find_license_files(self, files: List[FileInfo]) -> List[FileInfo]:
        """Find license files in the project"""
        return self.find_files_by_pattern(files, r"(?i)^(license|licence|copying)(\.(txt|md))?$")
    
    def find_readme_files(self, files: List[FileInfo]) -> List[FileInfo]:
        """Find README files in the project, prioritizing the most important one"""
        # Find all README files
        all_readme_files = self.find_files_by_pattern(files, r"(?i)readme(\.(md|rst|txt))?$")
        
        if not all_readme_files:
            return []
        
        # Prioritize README files by importance
        # 1. Root README.md (highest priority)
        # 2. docs/README.md (second priority - often contains main project description)
        # 3. Other README files
        
        root_readme = [f for f in all_readme_files if f.path.lower() == "readme.md"]
        docs_readme = [f for f in all_readme_files if f.path.lower() == "docs/readme.md"]
        other_readme = [f for f in all_readme_files if f.path.lower() not in ["readme.md", "docs/readme.md"]]
        
        # Return in priority order
        return root_readme + docs_readme + other_readme
    
    def find_bom_files(self, files: List[FileInfo]) -> List[FileInfo]:
        """Find BOM files in the project"""
        return self.find_files_by_pattern(files, r"(?i)^(bom|bill.of.materials|materials)(\.(txt|md|csv|json))?$")
    
    def get_text_files(self, files: List[FileInfo]) -> List[FileInfo]:
        """Get all text files from the project"""
        return [f for f in files if self.is_text_file(f.path)]
    
    def get_image_files(self, files: List[FileInfo]) -> List[FileInfo]:
        """Get all image files from the project"""
        return [f for f in files if self.is_image_file(f.path)]
    
    def get_design_files(self, files: List[FileInfo]) -> List[FileInfo]:
        """Get all design files from the project"""
        return [f for f in files if self.is_design_file(f.path)]