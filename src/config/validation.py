"""
Validation configuration settings.

This module provides configuration settings for the validation framework.
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class ValidationConfig:
    """Configuration for validation framework"""
    default_quality_level: str = "professional"
    strict_mode_default: bool = False
    validation_timeout: int = 30  # seconds
    max_validation_errors: int = 100
    enable_caching: bool = True
    cache_ttl: int = 3600  # seconds
    enable_domain_detection: bool = True
    enable_quality_level_validation: bool = True
    
    # Domain-specific settings
    manufacturing_settings: Dict[str, Any] = None
    cooking_settings: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize default domain settings"""
        if self.manufacturing_settings is None:
            self.manufacturing_settings = {
                "default_quality_level": "professional",
                "supported_quality_levels": ["hobby", "professional", "medical"],
                "enable_tsdc_validation": True,
                "require_manufacturing_specs": True
            }
        
        if self.cooking_settings is None:
            self.cooking_settings = {
                "default_quality_level": "home",
                "supported_quality_levels": ["home", "commercial", "professional"],
                "enable_food_safety_validation": True,
                "require_allergen_info": False
            }
    
    def get_domain_config(self, domain: str) -> Dict[str, Any]:
        """Get configuration for a specific domain"""
        if domain == "manufacturing":
            return self.manufacturing_settings
        elif domain == "cooking":
            return self.cooking_settings
        else:
            return {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "default_quality_level": self.default_quality_level,
            "strict_mode_default": self.strict_mode_default,
            "validation_timeout": self.validation_timeout,
            "max_validation_errors": self.max_validation_errors,
            "enable_caching": self.enable_caching,
            "cache_ttl": self.cache_ttl,
            "enable_domain_detection": self.enable_domain_detection,
            "enable_quality_level_validation": self.enable_quality_level_validation,
            "manufacturing_settings": self.manufacturing_settings,
            "cooking_settings": self.cooking_settings
        }


# Global validation configuration
VALIDATION_CONFIG = ValidationConfig()
