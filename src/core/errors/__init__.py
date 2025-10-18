"""
Core error handling system for the Open Matching Engine

This module provides a comprehensive error handling system with standardized
error types, exception hierarchy, and error handling patterns for all components
of the OME system, including LLM operations.
"""

from .exceptions import (
    # Base exceptions
    OMEError,
    ConfigurationError,
    ValidationError,
    ServiceError,
    APIError,
    
    # LLM-specific exceptions
    LLMError,
    LLMProviderError,
    LLMConfigurationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMAuthenticationError,
    LLMQuotaExceededError,
    
    # Service-specific exceptions
    GenerationError,
    MatchingError,
    StorageError,
    DomainError,
    
    # API-specific exceptions
    APIValidationError,
    APIAuthenticationError,
    APIRateLimitError,
    APINotFoundError,
    APIServerError,
    
    # Configuration exceptions
    ConfigValidationError,
    ConfigNotFoundError,
    ConfigPermissionError
)

from .handlers import (
    ErrorHandler,
    LLMErrorHandler,
    APIErrorHandler,
    ServiceErrorHandler,
    get_error_handler
)

from .logging import (
    LLMLogger,
    PerformanceLogger,
    AuditLogger,
    get_llm_logger,
    get_performance_logger,
    get_audit_logger,
    setup_enhanced_logging
)

from .metrics import (
    ErrorMetrics,
    PerformanceMetrics,
    LLMMetrics,
    get_error_metrics,
    get_performance_metrics,
    get_llm_metrics
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
    "get_llm_metrics"
]
