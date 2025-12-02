"""
Validation middleware for API endpoints.

This package provides middleware for standardized error handling
and request/response validation.
"""

from .error_handler import ValidationErrorHandler

__all__ = ["ValidationErrorHandler"]
