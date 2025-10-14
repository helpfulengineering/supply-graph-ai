"""
Base classes for generation layers.

This module defines the abstract base classes and interfaces that all
generation layers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from enum import Enum

from ..models import ProjectData, FieldGeneration, GenerationLayer as LayerType


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
    """Abstract base class for all generation layers"""
    
    def __init__(self, layer_type: LayerType):
        self.layer_type = layer_type
        self.config: Dict[str, Any] = {}
    
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
    
    def set_config(self, config: Dict[str, Any]):
        """Set layer configuration"""
        self.config = config
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)