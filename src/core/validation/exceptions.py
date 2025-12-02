"""
Validation-specific exceptions.

This module provides custom exceptions for validation operations.
"""


class ValidationException(Exception):
    """Base exception for validation errors"""

    pass


class ValidationContextError(ValidationException):
    """Exception for validation context errors"""

    pass


class DomainValidationError(ValidationException):
    """Exception for domain-specific validation errors"""

    pass


class ValidationRuleError(ValidationException):
    """Exception for validation rule errors"""

    pass


class ValidationEngineError(ValidationException):
    """Exception for validation engine errors"""

    pass
