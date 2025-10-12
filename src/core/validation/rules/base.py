"""
Base validation rules class.

This module provides the base class for domain-specific validation rules.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseValidationRules(ABC):
    """Base class for domain-specific validation rules"""
    
    @abstractmethod
    def get_validation_rules(self, quality_level: str) -> Dict[str, Any]:
        """Get validation rules for a specific quality level"""
        pass
    
    @abstractmethod
    def get_required_fields(self, quality_level: str) -> List[str]:
        """Get required fields for a specific quality level"""
        pass
    
    @abstractmethod
    def get_optional_fields(self, quality_level: str) -> List[str]:
        """Get optional fields for a specific quality level"""
        pass
    
    def get_validation_strictness(self, quality_level: str) -> str:
        """Get validation strictness for a quality level"""
        strictness_mapping = {
            "hobby": "relaxed",
            "home": "relaxed", 
            "professional": "standard",
            "commercial": "standard",
            "medical": "strict"
        }
        return strictness_mapping.get(quality_level, "standard")
    
    def validate_quality_level(self, quality_level: str) -> bool:
        """Validate that a quality level is supported"""
        supported_levels = self.get_supported_quality_levels()
        return quality_level in supported_levels
    
    @abstractmethod
    def get_supported_quality_levels(self) -> List[str]:
        """Get list of supported quality levels for this domain"""
        pass
    
    def get_field_validation_rules(self, field_name: str, quality_level: str) -> Dict[str, Any]:
        """Get specific validation rules for a field"""
        return {
            "required": field_name in self.get_required_fields(quality_level),
            "optional": field_name in self.get_optional_fields(quality_level),
            "strictness": self.get_validation_strictness(quality_level)
        }
    
    def get_all_fields(self, quality_level: str) -> List[str]:
        """Get all fields (required + optional) for a quality level"""
        required = self.get_required_fields(quality_level)
        optional = self.get_optional_fields(quality_level)
        return list(set(required + optional))
    
    def get_missing_required_fields(self, data: Dict[str, Any], quality_level: str) -> List[str]:
        """Get list of missing required fields from data"""
        required_fields = self.get_required_fields(quality_level)
        missing = []
        
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                missing.append(field)
        
        return missing
    
    def get_present_optional_fields(self, data: Dict[str, Any], quality_level: str) -> List[str]:
        """Get list of present optional fields from data"""
        optional_fields = self.get_optional_fields(quality_level)
        present = []
        
        for field in optional_fields:
            if field in data and data[field] is not None and data[field] != "":
                present.append(field)
        
        return present
