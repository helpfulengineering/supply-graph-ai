"""
Error handlers for the Open Matching Engine

This module provides specialized error handlers for different types of errors,
ensuring consistent error handling patterns across all components of the system.
"""

import logging
from typing import Dict, Any, Optional, Type, Union
from datetime import datetime, timedelta
import asyncio
from contextlib import asynccontextmanager

from .exceptions import (
    OMEError, LLMError, APIError, ServiceError, ConfigurationError,
    LLMRateLimitError, LLMTimeoutError, LLMAuthenticationError,
    APIRateLimitError, APIValidationError, APIAuthenticationError,
    APINotFoundError, APIServerError, ErrorSeverity, ErrorCategory
)

logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Base error handler providing common error handling patterns.
    
    This class provides standardized error handling with logging, metrics,
    and recovery strategies for different types of errors.
    """
    
    def __init__(self, component_name: str):
        self.component_name = component_name
        self.logger = logging.getLogger(f"{__name__}.{component_name}")
        self.error_counts: Dict[str, int] = {}
        self.last_error_times: Dict[str, datetime] = {}
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> Dict[str, Any]:
        """
        Handle an error with standardized logging and metrics.
        
        Args:
            error: The exception that occurred
            context: Additional context information
            severity: Error severity level
            
        Returns:
            Dictionary with error handling information
        """
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "severity": severity.value,
            "component": self.component_name,
            "timestamp": datetime.now().isoformat(),
            "context": context or {}
        }
        
        # Log the error
        self._log_error(error, error_info, severity)
        
        # Update metrics
        self._update_error_metrics(error, severity)
        
        # Determine if error should be raised or handled gracefully
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.error(f"Critical error in {self.component_name}: {error}")
            raise error
        else:
            self.logger.warning(f"Error handled in {self.component_name}: {error}")
            return error_info
    
    def _log_error(self, error: Exception, error_info: Dict[str, Any], severity: ErrorSeverity):
        """Log error with appropriate level based on severity"""
        log_data = {
            "error_info": error_info,
            "traceback": getattr(error, 'traceback', None)
        }
        
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"Critical error: {error}", extra=log_data)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(f"High severity error: {error}", extra=log_data)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"Medium severity error: {error}", extra=log_data)
        else:
            self.logger.info(f"Low severity error: {error}", extra=log_data)
    
    def _update_error_metrics(self, error: Exception, severity: ErrorSeverity):
        """Update error metrics and tracking"""
        error_type = type(error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self.last_error_times[error_type] = datetime.now()
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics for this handler"""
        return {
            "component": self.component_name,
            "error_counts": self.error_counts.copy(),
            "last_error_times": {
                error_type: time.isoformat()
                for error_type, time in self.last_error_times.items()
            }
        }


class LLMErrorHandler(ErrorHandler):
    """
    Specialized error handler for LLM-related errors.
    
    Provides specific handling for LLM provider errors, rate limits,
    timeouts, and authentication issues with appropriate retry logic.
    """
    
    def __init__(self, component_name: str = "llm"):
        super().__init__(component_name)
        self.retry_counts: Dict[str, int] = {}
        self.rate_limit_backoffs: Dict[str, datetime] = {}
    
    def handle_llm_error(
        self,
        error: LLMError,
        provider: str,
        operation: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle LLM-specific errors with appropriate recovery strategies.
        
        Args:
            error: The LLM error that occurred
            provider: LLM provider name
            operation: Operation that failed
            context: Additional context
            
        Returns:
            Error handling information with recovery suggestions
        """
        error_key = f"{provider}:{operation}"
        context = context or {}
        context.update({
            "provider": provider,
            "operation": operation,
            "error_key": error_key
        })
        
        # Handle specific LLM error types
        if isinstance(error, LLMRateLimitError):
            return self._handle_rate_limit_error(error, provider, context)
        elif isinstance(error, LLMTimeoutError):
            return self._handle_timeout_error(error, provider, context)
        elif isinstance(error, LLMAuthenticationError):
            return self._handle_auth_error(error, provider, context)
        else:
            return self._handle_generic_llm_error(error, provider, context)
    
    def _handle_rate_limit_error(
        self,
        error: LLMRateLimitError,
        provider: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle LLM rate limit errors with backoff strategy"""
        retry_after = error.details.get('retry_after', 60)
        backoff_until = datetime.now() + timedelta(seconds=retry_after)
        self.rate_limit_backoffs[provider] = backoff_until
        
        self.logger.warning(
            f"Rate limit exceeded for {provider}, backing off until {backoff_until}",
            extra={"error": error.to_dict(), "context": context}
        )
        
        return {
            "error_type": "rate_limit",
            "provider": provider,
            "retry_after": retry_after,
            "backoff_until": backoff_until.isoformat(),
            "suggestion": "retry_after_backoff",
            "severity": ErrorSeverity.MEDIUM.value
        }
    
    def _handle_timeout_error(
        self,
        error: LLMTimeoutError,
        provider: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle LLM timeout errors with retry strategy"""
        timeout_seconds = error.details.get('timeout_seconds', 30)
        
        self.logger.warning(
            f"Timeout for {provider} after {timeout_seconds}s",
            extra={"error": error.to_dict(), "context": context}
        )
        
        return {
            "error_type": "timeout",
            "provider": provider,
            "timeout_seconds": timeout_seconds,
            "suggestion": "retry_with_longer_timeout",
            "severity": ErrorSeverity.MEDIUM.value
        }
    
    def _handle_auth_error(
        self,
        error: LLMAuthenticationError,
        provider: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle LLM authentication errors"""
        self.logger.error(
            f"Authentication failed for {provider}",
            extra={"error": error.to_dict(), "context": context}
        )
        
        return {
            "error_type": "authentication",
            "provider": provider,
            "suggestion": "check_api_key",
            "severity": ErrorSeverity.HIGH.value
        }
    
    def _handle_generic_llm_error(
        self,
        error: LLMError,
        provider: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle generic LLM errors"""
        self.logger.error(
            f"LLM error for {provider}: {error}",
            extra={"error": error.to_dict(), "context": context}
        )
        
        return {
            "error_type": "generic_llm_error",
            "provider": provider,
            "suggestion": "check_provider_status",
            "severity": ErrorSeverity.MEDIUM.value
        }
    
    def can_retry(self, provider: str, operation: str) -> bool:
        """Check if an operation can be retried for a provider"""
        error_key = f"{provider}:{operation}"
        retry_count = self.retry_counts.get(error_key, 0)
        
        # Check rate limit backoff
        if provider in self.rate_limit_backoffs:
            if datetime.now() < self.rate_limit_backoffs[provider]:
                return False
        
        # Limit retries
        return retry_count < 3
    
    def record_retry(self, provider: str, operation: str):
        """Record a retry attempt"""
        error_key = f"{provider}:{operation}"
        self.retry_counts[error_key] = self.retry_counts.get(error_key, 0) + 1


class APIErrorHandler(ErrorHandler):
    """
    Specialized error handler for API-related errors.
    
    Provides specific handling for HTTP errors, validation errors,
    and API-specific issues with appropriate status codes and responses.
    """
    
    def __init__(self, component_name: str = "api"):
        super().__init__(component_name)
    
    def handle_api_error(
        self,
        error: APIError,
        endpoint: str,
        method: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle API-specific errors with appropriate HTTP status codes.
        
        Args:
            error: The API error that occurred
            endpoint: API endpoint that failed
            method: HTTP method
            context: Additional context
            
        Returns:
            Error handling information with HTTP status code
        """
        context = context or {}
        context.update({
            "endpoint": endpoint,
            "method": method
        })
        
        # Determine HTTP status code based on error type
        status_code = self._get_status_code(error)
        
        error_info = {
            "error_type": type(error).__name__,
            "status_code": status_code,
            "endpoint": endpoint,
            "method": method,
            "message": str(error),
            "details": getattr(error, 'details', {}),
            "timestamp": datetime.now().isoformat()
        }
        
        # Log the error
        self.logger.error(
            f"API error on {method} {endpoint}: {error}",
            extra={"error_info": error_info, "context": context}
        )
        
        return error_info
    
    def _get_status_code(self, error: APIError) -> int:
        """Get appropriate HTTP status code for API error"""
        if isinstance(error, APIValidationError):
            return 400
        elif isinstance(error, APIAuthenticationError):
            return 401
        elif isinstance(error, APIRateLimitError):
            return 429
        elif isinstance(error, APINotFoundError):
            return 404
        elif isinstance(error, APIServerError):
            return getattr(error, 'details', {}).get('status_code', 500)
        else:
            return 500


class ServiceErrorHandler(ErrorHandler):
    """
    Specialized error handler for service-related errors.
    
    Provides specific handling for service initialization, operation,
    and lifecycle errors with appropriate recovery strategies.
    """
    
    def __init__(self, component_name: str = "service"):
        super().__init__(component_name)
    
    def handle_service_error(
        self,
        error: ServiceError,
        service_name: str,
        operation: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle service-specific errors with appropriate recovery.
        
        Args:
            error: The service error that occurred
            service_name: Name of the service
            operation: Operation that failed
            context: Additional context
            
        Returns:
            Error handling information with recovery suggestions
        """
        context = context or {}
        context.update({
            "service_name": service_name,
            "operation": operation
        })
        
        error_info = {
            "error_type": type(error).__name__,
            "service_name": service_name,
            "operation": operation,
            "message": str(error),
            "details": getattr(error, 'details', {}),
            "timestamp": datetime.now().isoformat()
        }
        
        # Log the error
        self.logger.error(
            f"Service error in {service_name} during {operation}: {error}",
            extra={"error_info": error_info, "context": context}
        )
        
        return error_info


# Global error handler registry
_error_handlers: Dict[str, ErrorHandler] = {}


def get_error_handler(component_name: str, handler_type: str = "generic") -> ErrorHandler:
    """
    Get or create an error handler for a component.
    
    Args:
        component_name: Name of the component
        handler_type: Type of handler (generic, llm, api, service)
        
    Returns:
        Appropriate error handler instance
    """
    handler_key = f"{component_name}:{handler_type}"
    
    if handler_key not in _error_handlers:
        if handler_type == "llm":
            _error_handlers[handler_key] = LLMErrorHandler(component_name)
        elif handler_type == "api":
            _error_handlers[handler_key] = APIErrorHandler(component_name)
        elif handler_type == "service":
            _error_handlers[handler_key] = ServiceErrorHandler(component_name)
        else:
            _error_handlers[handler_key] = ErrorHandler(component_name)
    
    return _error_handlers[handler_key]


@asynccontextmanager
async def error_context(
    component_name: str,
    operation: str,
    handler_type: str = "generic",
    context: Optional[Dict[str, Any]] = None
):
    """
    Context manager for error handling with automatic cleanup.
    
    Args:
        component_name: Name of the component
        operation: Operation being performed
        handler_type: Type of error handler
        context: Additional context
        
    Yields:
        Error handler instance
    """
    handler = get_error_handler(component_name, handler_type)
    context = context or {}
    context["operation"] = operation
    
    try:
        yield handler
    except Exception as e:
        handler.handle_error(e, context)
        raise
