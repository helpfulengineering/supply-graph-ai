"""
Base classes and enums for generation layers.

This module defines the base interfaces and enums used by all generation layers.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any

from ..models import ProjectData, FieldGeneration


class GenerationLayer(Enum):
    """Available generation layers"""
    DIRECT = "direct"      # Direct field mapping
    HEURISTIC = "heuristic"  # Rule-based pattern recognition
    NLP = "nlp"           # Natural language processing
    LLM = "llm"           # Large language model


class BaseLayerMatcher(ABC):
    """Abstract base class for generation layer matchers"""
    
    @abstractmethod
    def generate_fields(self, project_data: ProjectData) -> Dict[str, FieldGeneration]:
        """
        Generate manifest fields using this layer's approach.
        
        Args:
            project_data: Raw project data from platform
            
        Returns:
            Dictionary mapping field names to FieldGeneration objects
        """
        pass
    
    @abstractmethod
    def get_layer_type(self) -> GenerationLayer:
        """
        Get the type of this generation layer.
        
        Returns:
            GenerationLayer enum value
        """
        pass
    
    def get_confidence_threshold(self) -> float:
        """
        Get the minimum confidence threshold for this layer.
        
        Returns:
            Confidence threshold (0.0 to 1.0)
        """
        return 0.8  # Default threshold
