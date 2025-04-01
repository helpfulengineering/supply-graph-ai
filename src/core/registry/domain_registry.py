from typing import Dict, Type, Any
from ..models.base_extractors import BaseExtractor

class DomainRegistry:
    """Registry for domain-specific components"""
    _extractors: Dict[str, BaseExtractor] = {}
    _matchers: Dict[str, Any] = {}
    _validators: Dict[str, Any] = {}
    
    @classmethod
    def register_extractor(cls, domain: str, extractor: BaseExtractor) -> None:
        """Register an extractor for a specific domain"""
        cls._extractors[domain] = extractor
    
    @classmethod
    def register_matcher(cls, domain: str, matcher: Any) -> None:
        """Register a matcher for a specific domain"""
        cls._matchers[domain] = matcher
    
    @classmethod
    def register_validator(cls, domain: str, validator: Any) -> None:
        """Register a validator for a specific domain"""
        cls._validators[domain] = validator
    
    @classmethod
    def get_extractor(cls, domain: str) -> BaseExtractor:
        """Get registered extractor for domain"""
        if domain not in cls._extractors:
            raise ValueError(f"No extractor registered for domain: {domain}")
        return cls._extractors[domain]
    
    @classmethod
    def get_matcher(cls, domain: str) -> Any:
        """Get registered matcher for domain"""
        if domain not in cls._matchers:
            raise ValueError(f"No matcher registered for domain: {domain}")
        return cls._matchers[domain]
    
    @classmethod
    def get_validator(cls, domain: str) -> Any:
        """Get registered validator for domain"""
        if domain not in cls._validators:
            raise ValueError(f"No validator registered for domain: {domain}")
        return cls._validators[domain]