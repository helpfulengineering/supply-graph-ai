"""
Standardized error response middleware.

This module provides middleware for consistent error responses
across all validation endpoints.
"""

import logging
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from ..exceptions import (
    DomainValidationError,
    ValidationContextError,
    ValidationException,
)

logger = logging.getLogger(__name__)


class ValidationErrorHandler:
    """Middleware for handling validation errors consistently"""

    @staticmethod
    def create_error_response(
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 400,
    ) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "error": {"code": error_code, "message": message, "details": details or {}}
        }

    @staticmethod
    def handle_validation_exception(exception: ValidationException) -> JSONResponse:
        """Handle validation exceptions with appropriate HTTP status codes"""
        if isinstance(exception, ValidationContextError):
            return JSONResponse(
                status_code=400,
                content=ValidationErrorHandler.create_error_response(
                    "validation_context_error",
                    str(exception),
                    {"type": "ValidationContextError"},
                ),
            )
        elif isinstance(exception, DomainValidationError):
            return JSONResponse(
                status_code=422,
                content=ValidationErrorHandler.create_error_response(
                    "domain_validation_error",
                    str(exception),
                    {"type": "DomainValidationError"},
                ),
            )
        else:
            return JSONResponse(
                status_code=422,
                content=ValidationErrorHandler.create_error_response(
                    "validation_error", str(exception), {"type": "ValidationException"}
                ),
            )

    @staticmethod
    def handle_http_exception(exception: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions with standardized format"""
        return JSONResponse(
            status_code=exception.status_code,
            content=ValidationErrorHandler.create_error_response(
                "http_error", exception.detail, {"status_code": exception.status_code}
            ),
        )

    @staticmethod
    def handle_generic_exception(exception: Exception) -> JSONResponse:
        """Handle generic exceptions with standardized format"""
        logger.error(f"Unexpected validation error: {str(exception)}", exc_info=True)

        return JSONResponse(
            status_code=500,
            content=ValidationErrorHandler.create_error_response(
                "internal_error",
                "An unexpected error occurred during validation",
                {"type": type(exception).__name__},
            ),
        )

    @staticmethod
    def create_validation_failed_response(
        validation_result: Any, validation_type: str, context: Optional[str] = None
    ) -> JSONResponse:
        """Create standardized response for failed validation"""
        # Convert validation result to standardized format
        if hasattr(validation_result, "to_dict"):
            result_dict = validation_result.to_dict()
        elif isinstance(validation_result, dict):
            result_dict = validation_result
        else:
            result_dict = {"valid": False, "errors": [str(validation_result)]}

        return JSONResponse(
            status_code=422,
            content=ValidationErrorHandler.create_error_response(
                "validation_failed",
                f"Validation failed for {validation_type}",
                {
                    "validation_type": validation_type,
                    "context": context,
                    "validation_result": result_dict,
                },
            ),
        )

    @staticmethod
    def create_success_response(
        validation_result: Any, validation_type: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create standardized response for successful validation"""
        # Convert validation result to standardized format
        if hasattr(validation_result, "to_dict"):
            result_dict = validation_result.to_dict()
        elif isinstance(validation_result, dict):
            result_dict = validation_result
        else:
            result_dict = {"valid": True}

        return {
            "success": True,
            "validation_type": validation_type,
            "context": context,
            "validation_result": result_dict,
        }

    @staticmethod
    def get_http_status_for_validation_result(validation_result: Any) -> int:
        """Get appropriate HTTP status code for validation result"""
        if hasattr(validation_result, "valid"):
            if validation_result.valid:
                return 200
            else:
                return 422
        elif isinstance(validation_result, dict):
            if validation_result.get("valid", False):
                return 200
            else:
                return 422
        else:
            return 200
