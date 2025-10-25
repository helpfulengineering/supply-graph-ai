"""
Validation context with domain integration.

This module provides the ValidationContext class that integrates
with the existing domain management system.
"""

from dataclasses import dataclass, field
from typing import Dict, Any
from src.core.registry.domain_registry import DomainRegistry

@dataclass
class ValidationContext:
    """Context for validation operations - integrates with existing domain system"""
    name: str
    domain: str  # Must be a registered domain from DomainRegistry
    quality_level: str  # 'hobby', 'professional', 'medical'
    strict_mode: bool = False
    custom_rules: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate that domain exists in registry"""
        if self.domain not in DomainRegistry.list_domains():
            raise ValueError(f"Domain '{self.domain}' is not registered. Available domains: {DomainRegistry.list_domains()}")
    
    def get_domain_services(self):
        """Get domain services for this context"""
        return DomainRegistry.get_domain_services(self.domain)
    
    def get_domain_validator(self):
        """Get domain-specific validator"""
        return self.get_domain_services().validator
    
    def get_domain_metadata(self):
        """Get domain metadata for this context"""
        return self.get_domain_services().metadata
    
    def is_quality_level_valid(self) -> bool:
        """Check if the quality level is valid for this domain"""
        # Define valid quality levels per domain
        valid_quality_levels = {
            "manufacturing": ["hobby", "professional", "medical"],
            "cooking": ["home", "commercial", "professional"]
        }
        
        domain_quality_levels = valid_quality_levels.get(self.domain, ["professional"])
        return self.quality_level in domain_quality_levels
    
    def get_validation_strictness(self) -> str:
        """Get validation strictness based on quality level and strict mode"""
        if self.strict_mode:
            return "strict"
        
        strictness_mapping = {
            "hobby": "relaxed",
            "home": "relaxed",
            "professional": "standard",
            "commercial": "standard",
            "medical": "strict"
        }
        
        return strictness_mapping.get(self.quality_level, "standard")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "name": self.name,
            "domain": self.domain,
            "quality_level": self.quality_level,
            "strict_mode": self.strict_mode,
            "custom_rules": self.custom_rules,
            "validation_strictness": self.get_validation_strictness()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidationContext':
        """Create ValidationContext from dictionary"""
        return cls(
            name=data["name"],
            domain=data["domain"],
            quality_level=data["quality_level"],
            strict_mode=data.get("strict_mode", False),
            custom_rules=data.get("custom_rules", {})
        )
