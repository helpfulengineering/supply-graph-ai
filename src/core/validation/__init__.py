"""
Core validation framework for the Open Hardware Manager.

This package provides a domain-integrated validation system that works
seamlessly with the existing domain management infrastructure.
"""

from .context import ValidationContext
from .engine import ValidationEngine
from .exceptions import (
    DomainValidationError,
    ValidationContextError,
    ValidationEngineError,
    ValidationException,
    ValidationRuleError,
)
from .factory import ValidationContextFactory
from .result import ValidationError, ValidationResult, ValidationWarning

__all__ = [
    "ValidationEngine",
    "ValidationContext",
    "ValidationResult",
    "ValidationError",
    "ValidationWarning",
    "ValidationContextFactory",
    "ValidationException",
    "ValidationContextError",
    "DomainValidationError",
    "ValidationRuleError",
    "ValidationEngineError",
]
