"""
Standardized error handlers for API routes.

This module provides consistent error handling across all API endpoints
with proper HTTP status codes and structured error responses.
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Union
import logging
import traceback
from datetime import datetime

from .models.base import ErrorResponse, ErrorDetail, ErrorCode, APIStatus, SuccessResponse
from ..errors.exceptions import (
    OMEError, 
    ValidationError, 
    ServiceError, 
    LLMError, 
    APIError,
    ConfigurationError
)
from ..errors.handlers import ErrorHandler

# Set up logging
logger = logging.getLogger(__name__)


class APIErrorHandler:
    """Standardized error handler for API endpoints."""
    
    def __init__(self):
        self.error_handler = ErrorHandler("api")
    
    def create_error_response(
        self,
        error: Union[Exception, str],
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        request_id: str = None,
        field: str = None,
        value: any = None,
        suggestion: str = None
    ) -> ErrorResponse:
        """
        Create a standardized error response.
        
        Args:
            error: The error or error message
            status_code: HTTP status code
            request_id: Request identifier for tracking
            field: Field that caused the error
            value: Value that caused the error
            suggestion: Suggested fix
            
        Returns:
            Standardized error response
        """
        if isinstance(error, str):
            error_message = error
            error_code = ErrorCode.INTERNAL_ERROR
        elif isinstance(error, OMEError):
            error_message = str(error)
            error_code = self._map_ome_error_to_code(error)
        else:
            error_message = str(error)
            error_code = ErrorCode.INTERNAL_ERROR
        
        error_detail = ErrorDetail(
            code=error_code,
            message=error_message,
            field=field,
            value=value,
            suggestion=suggestion
        )
        
        return ErrorResponse(
            status=APIStatus.ERROR,
            message=f"Request failed: {error_message}",
            timestamp=datetime.now(),
            request_id=request_id,
            errors=[error_detail],
            error_count=1,
            data=None,
            metadata={
                "status_code": status_code,
                "error_type": type(error).__name__ if not isinstance(error, str) else "StringError"
            }
        )
    
    def _map_ome_error_to_code(self, error: OMEError) -> ErrorCode:
        """Map OME error types to standard error codes."""
        if isinstance(error, ValidationError):
            return ErrorCode.VALIDATION_ERROR
        elif isinstance(error, ServiceError):
            return ErrorCode.SERVICE_UNAVAILABLE
        elif isinstance(error, LLMError):
            return ErrorCode.LLM_UNAVAILABLE
        elif isinstance(error, APIError):
            return ErrorCode.INTERNAL_ERROR
        elif isinstance(error, ConfigurationError):
            return ErrorCode.INTERNAL_ERROR
        else:
            return ErrorCode.INTERNAL_ERROR
    
    def handle_validation_error(
        self, 
        error: RequestValidationError, 
        request_id: str = None
    ) -> ErrorResponse:
        """Handle FastAPI validation errors."""
        errors = []
        
        for validation_error in error.errors():
            field = ".".join(str(loc) for loc in validation_error["loc"])
            error_detail = ErrorDetail(
                code=ErrorCode.VALIDATION_ERROR,
                message=validation_error["msg"],
                field=field,
                value=validation_error.get("input"),
                suggestion=self._get_validation_suggestion(validation_error)
            )
            errors.append(error_detail)
        
        return ErrorResponse(
            status=APIStatus.ERROR,
            message=f"Request validation failed: {len(errors)} error(s)",
            timestamp=datetime.now(),
            request_id=request_id,
            errors=errors,
            error_count=len(errors),
            data=None,
            metadata={
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "error_type": "ValidationError"
            }
        )
    
    def _get_validation_suggestion(self, validation_error: dict) -> str:
        """Get a helpful suggestion for validation errors."""
        error_type = validation_error.get("type", "")
        
        suggestions = {
            "value_error.missing": "This field is required",
            "value_error.str.regex": "Please check the format of this field",
            "type_error.integer": "This field must be a number",
            "type_error.float": "This field must be a decimal number",
            "type_error.bool": "This field must be true or false",
            "type_error.list": "This field must be a list",
            "type_error.dict": "This field must be an object",
            "value_error.uuid": "This field must be a valid UUID",
            "value_error.email": "This field must be a valid email address",
            "value_error.url": "This field must be a valid URL"
        }
        
        return suggestions.get(error_type, "Please check the value and try again")
    
    def handle_http_exception(
        self, 
        error: Union[HTTPException, StarletteHTTPException], 
        request_id: str = None
    ) -> ErrorResponse:
        """Handle HTTP exceptions."""
        error_code = self._map_http_status_to_code(error.status_code)
        
        error_detail = ErrorDetail(
            code=error_code,
            message=str(error.detail),
            suggestion=self._get_http_error_suggestion(error.status_code)
        )
        
        return ErrorResponse(
            status=APIStatus.ERROR,
            message=f"HTTP {error.status_code}: {error.detail}",
            timestamp=datetime.now(),
            request_id=request_id,
            errors=[error_detail],
            error_count=1,
            data=None,
            metadata={
                "status_code": error.status_code,
                "error_type": "HTTPException"
            }
        )
    
    def _map_http_status_to_code(self, status_code: int) -> ErrorCode:
        """Map HTTP status codes to error codes."""
        if status_code == 400:
            return ErrorCode.INVALID_INPUT
        elif status_code == 401:
            return ErrorCode.UNAUTHORIZED
        elif status_code == 403:
            return ErrorCode.FORBIDDEN
        elif status_code == 404:
            return ErrorCode.NOT_FOUND
        elif status_code == 409:
            return ErrorCode.ALREADY_EXISTS
        elif status_code == 422:
            return ErrorCode.VALIDATION_ERROR
        elif status_code == 429:
            return ErrorCode.RATE_LIMITED
        elif status_code == 500:
            return ErrorCode.INTERNAL_ERROR
        elif status_code == 503:
            return ErrorCode.SERVICE_UNAVAILABLE
        else:
            return ErrorCode.INTERNAL_ERROR
    
    def _get_http_error_suggestion(self, status_code: int) -> str:
        """Get helpful suggestions for HTTP errors."""
        suggestions = {
            400: "Please check your request parameters and try again",
            401: "Please provide valid authentication credentials",
            403: "You don't have permission to access this resource",
            404: "The requested resource was not found",
            409: "A resource with this identifier already exists",
            422: "Please check your request data and try again",
            429: "Too many requests. Please wait and try again",
            500: "An internal server error occurred. Please try again later",
            503: "Service temporarily unavailable. Please try again later"
        }
        
        return suggestions.get(status_code, "Please try again later")


# Global error handler instance
api_error_handler = APIErrorHandler()


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI validation exceptions."""
    request_id = getattr(request.state, 'request_id', None)
    error_response = api_error_handler.handle_validation_error(exc, request_id)
    
    logger.warning(
        f"Validation error in {request.method} {request.url}: {len(exc.errors())} error(s)",
        extra={
            "request_id": request_id,
            "errors": exc.errors(),
            "path": str(request.url.path)
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(mode='json')
    )


async def http_exception_handler(request: Request, exc: Union[HTTPException, StarletteHTTPException]):
    """Handle HTTP exceptions."""
    request_id = getattr(request.state, 'request_id', None)
    error_response = api_error_handler.handle_http_exception(exc, request_id)
    
    logger.warning(
        f"HTTP error in {request.method} {request.url}: {exc.status_code} - {exc.detail}",
        extra={
            "request_id": request_id,
            "status_code": exc.status_code,
            "path": str(request.url.path)
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode='json')
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    request_id = getattr(request.state, 'request_id', None)
    
    # Log the full exception for debugging
    logger.error(
        f"Unhandled exception in {request.method} {request.url}: {str(exc)}",
        extra={
            "request_id": request_id,
            "exception_type": type(exc).__name__,
            "path": str(request.url.path),
            "traceback": traceback.format_exc()
        },
        exc_info=True
    )
    
    # Create error response
    error_response = api_error_handler.create_error_response(
        error=exc,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request_id=request_id,
        suggestion="An unexpected error occurred. Please try again later."
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(by_alias=True, exclude_none=True, mode='json')
    )


def create_error_response(
    error: Union[Exception, str],
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    request_id: str = None,
    field: str = None,
    value: any = None,
    suggestion: str = None
) -> ErrorResponse:
    """
    Convenience function to create standardized error responses.
    
    Args:
        error: The error or error message
        status_code: HTTP status code
        request_id: Request identifier for tracking
        field: Field that caused the error
        value: Value that caused the error
        suggestion: Suggested fix
        
    Returns:
        Standardized error response
    """
    return api_error_handler.create_error_response(
        error=error,
        status_code=status_code,
        request_id=request_id,
        field=field,
        value=value,
        suggestion=suggestion
    )


def create_success_response(
    message: str,
    data: dict = None,
    request_id: str = None,
    metadata: dict = None
) -> SuccessResponse:
    """
    Convenience function to create standardized success responses.
    
    Args:
        message: Success message
        data: Response data
        request_id: Request identifier for tracking
        metadata: Additional metadata
        
    Returns:
        Standardized success response object
    """
    return SuccessResponse(
        status=APIStatus.SUCCESS,
        message=message,
        timestamp=datetime.now(),
        request_id=request_id,
        data=data or {},
        metadata=metadata or {}
    )
