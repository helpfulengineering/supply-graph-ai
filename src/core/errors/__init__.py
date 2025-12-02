"""
Core error handling system for the Open Matching Engine

This module provides a error handling system with standardized
error types, exception hierarchy, and error handling patterns for all components
of the OME system, including LLM operations.
"""

from .exceptions import (  # Base exceptions; LLM-specific exceptions; Service-specific exceptions; API-specific exceptions; Configuration exceptions
    APIAuthenticationError,
    APIError,
    APINotFoundError,
    APIRateLimitError,
    APIServerError,
    APIValidationError,
    ConfigNotFoundError,
    ConfigPermissionError,
    ConfigurationError,
    ConfigValidationError,
    DomainError,
    GenerationError,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMError,
    LLMProviderError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMTimeoutError,
    MatchingError,
    OMEError,
    ServiceError,
    StorageError,
    ValidationError,
)
from .handlers import (
    APIErrorHandler,
    ErrorHandler,
    LLMErrorHandler,
    ServiceErrorHandler,
    get_error_handler,
)
from .logging import (
    AuditLogger,
    LLMLogger,
    PerformanceLogger,
    get_audit_logger,
    get_llm_logger,
    get_performance_logger,
    setup_enhanced_logging,
)
from .metrics import (
    ErrorMetrics,
    LLMMetrics,
    PerformanceMetrics,
    get_error_metrics,
    get_llm_metrics,
    get_performance_metrics,
)

__all__ = [
    # Exceptions
    "OMEError",
    "ConfigurationError",
    "ValidationError",
    "ServiceError",
    "APIError",
    "LLMError",
    "LLMProviderError",
    "LLMConfigurationError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMAuthenticationError",
    "LLMQuotaExceededError",
    "GenerationError",
    "MatchingError",
    "StorageError",
    "DomainError",
    "APIValidationError",
    "APIAuthenticationError",
    "APIRateLimitError",
    "APINotFoundError",
    "APIServerError",
    "ConfigValidationError",
    "ConfigNotFoundError",
    "ConfigPermissionError",
    # Handlers
    "ErrorHandler",
    "LLMErrorHandler",
    "APIErrorHandler",
    "ServiceErrorHandler",
    "get_error_handler",
    # Logging
    "LLMLogger",
    "PerformanceLogger",
    "AuditLogger",
    "get_llm_logger",
    "get_performance_logger",
    "get_audit_logger",
    "setup_enhanced_logging",
    # Metrics
    "ErrorMetrics",
    "PerformanceMetrics",
    "LLMMetrics",
    "get_error_metrics",
    "get_performance_metrics",
    "get_llm_metrics",
]
