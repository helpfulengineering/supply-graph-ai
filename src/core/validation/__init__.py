"""
Core validation framework for the Open Matching Engine.

This package provides a domain-integrated validation system that works
seamlessly with the existing domain management infrastructure.
"""

from .engine import ValidationEngine
from .context import ValidationContext
from .result import ValidationResult, ValidationError, ValidationWarning
from .factory import ValidationContextFactory
from .exceptions import (
    ValidationException,
    ValidationContextError,
    DomainValidationError,
    ValidationRuleError,
    ValidationEngineError,
)

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
