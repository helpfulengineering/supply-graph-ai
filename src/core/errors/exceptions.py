"""
Comprehensive exception hierarchy for the Open Matching Engine

This module defines a standardized exception hierarchy that provides
clear error categorization, context, and handling patterns for all
components of the OME system.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import traceback
from datetime import datetime


class ErrorSeverity(Enum):
    """Severity levels for errors"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors"""

    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    SERVICE = "service"
    API = "api"
    LLM = "llm"
    STORAGE = "storage"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    QUOTA = "quota"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for errors"""

    component: str
    operation: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class OMEError(Exception):
    """
    Base exception class for all OME errors.

    Provides standardized error handling with context, severity,
    and categorization for consistent error management across
    the entire system.
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or ErrorContext(component="unknown", operation="unknown")
        self.cause = cause
        self.error_code = error_code or f"{category.value}_{severity.value}"
        self.details = details or {}
        self.timestamp = datetime.now()
        self.traceback = traceback.format_exc()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": {
                "component": self.context.component,
                "operation": self.context.operation,
                "user_id": self.context.user_id,
                "request_id": self.context.request_id,
                "session_id": self.context.session_id,
                "timestamp": self.context.timestamp.isoformat(),
                "metadata": self.context.metadata,
            },
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None,
        }

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


# Configuration Errors
class ConfigurationError(OMEError):
    """Base class for configuration-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.CONFIGURATION, **kwargs)


class ConfigValidationError(ConfigurationError):
    """Configuration validation failed"""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        kwargs["details"] = details
        super().__init__(message, **kwargs)


class ConfigNotFoundError(ConfigurationError):
    """Configuration file or setting not found"""

    def __init__(self, message: str, config_path: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if config_path:
            details["config_path"] = config_path
        kwargs["details"] = details
        super().__init__(message, **kwargs)


class ConfigPermissionError(ConfigurationError):
    """Insufficient permissions to access configuration"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, **kwargs)


# Validation Errors
class ValidationError(OMEError):
    """Base class for validation-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.VALIDATION, **kwargs)


# Service Errors
class ServiceError(OMEError):
    """Base class for service-related errors"""

    def __init__(self, message: str, service_name: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if service_name:
            details["service_name"] = service_name
        kwargs["details"] = details
        super().__init__(message, category=ErrorCategory.SERVICE, **kwargs)


class GenerationError(ServiceError):
    """Generation service errors"""

    def __init__(self, message: str, layer: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if layer:
            details["layer"] = layer
        kwargs["details"] = details
        super().__init__(message, service_name="generation", **kwargs)


class MatchingError(ServiceError):
    """Matching service errors"""

    def __init__(self, message: str, layer: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if layer:
            details["layer"] = layer
        kwargs["details"] = details
        super().__init__(message, service_name="matching", **kwargs)


class StorageError(ServiceError):
    """Storage service errors"""

    def __init__(self, message: str, storage_type: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if storage_type:
            details["storage_type"] = storage_type
        kwargs["details"] = details
        super().__init__(message, service_name="storage", **kwargs)


class DomainError(ServiceError):
    """Domain-specific errors"""

    def __init__(self, message: str, domain: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if domain:
            details["domain"] = domain
        kwargs["details"] = details
        super().__init__(message, service_name="domain", **kwargs)


# LLM Errors
class LLMError(OMEError):
    """Base class for LLM-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.LLM, **kwargs)


class LLMProviderError(LLMError):
    """LLM provider-specific errors"""

    def __init__(self, message: str, provider: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if provider:
            details["provider"] = provider
        kwargs["details"] = details
        super().__init__(message, **kwargs)


class LLMConfigurationError(LLMError):
    """LLM configuration errors"""

    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if config_key:
            details["config_key"] = config_key
        kwargs["details"] = details
        super().__init__(message, **kwargs)


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded"""

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        details = kwargs.get("details", {})
        if retry_after:
            details["retry_after"] = retry_after
        kwargs["details"] = details
        super().__init__(message, **kwargs)


class LLMTimeoutError(LLMError):
    """LLM request timeout"""

    def __init__(self, message: str, timeout_seconds: Optional[float] = None, **kwargs):
        details = kwargs.get("details", {})
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        kwargs["details"] = details
        super().__init__(message, **kwargs)


class LLMAuthenticationError(LLMError):
    """LLM authentication failed"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, **kwargs)


class LLMQuotaExceededError(LLMError):
    """LLM quota exceeded"""

    def __init__(self, message: str, quota_type: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if quota_type:
            details["quota_type"] = quota_type
        kwargs["details"] = details
        super().__init__(message, **kwargs)


# API Errors
class APIError(OMEError):
    """Base class for API-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.API, **kwargs)


class APIValidationError(APIError):
    """API request validation failed"""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        kwargs["details"] = details
        super().__init__(message, **kwargs)


class APIAuthenticationError(APIError):
    """API authentication failed"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, **kwargs)


class APIRateLimitError(APIError):
    """API rate limit exceeded"""

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        details = kwargs.get("details", {})
        if retry_after:
            details["retry_after"] = retry_after
        kwargs["details"] = details
        super().__init__(message, **kwargs)


class APINotFoundError(APIError):
    """API resource not found"""

    def __init__(self, message: str, resource: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if resource:
            details["resource"] = resource
        kwargs["details"] = details
        super().__init__(message, **kwargs)


class APIServerError(APIError):
    """API server error"""

    def __init__(self, message: str, status_code: Optional[int] = None, **kwargs):
        details = kwargs.get("details", {})
        if status_code:
            details["status_code"] = status_code
        kwargs["details"] = details
        super().__init__(message, **kwargs)
