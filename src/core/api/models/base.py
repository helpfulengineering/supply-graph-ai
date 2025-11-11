"""
Base models for API requests and responses.

This module provides standardized base classes and common models for all API endpoints
to ensure consistency across the Open Matching Engine API.
"""

from pydantic import BaseModel, Field, validator
from pydantic import ConfigDict
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from uuid import UUID
from enum import Enum


class APIStatus(str, Enum):
    """Standard API status values."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    
    # Authentication/Authorization errors
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_TOKEN = "INVALID_TOKEN"
    
    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    
    # Service errors
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    
    # LLM-specific errors
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
    LLM_INVALID_RESPONSE = "LLM_INVALID_RESPONSE"
    LLM_COST_LIMIT_EXCEEDED = "LLM_COST_LIMIT_EXCEEDED"


class BaseAPIRequest(BaseModel):
    """Base class for all API requests with common fields and validation."""
    
    # Optional metadata fields
    request_id: Optional[str] = Field(None, description="Unique request identifier for tracking")
    client_info: Optional[Dict[str, Any]] = Field(None, description="Client information and context")
    quality_level: Optional[str] = Field("professional", description="Quality level: hobby, professional, or medical")
    strict_mode: Optional[bool] = Field(False, description="Enable strict validation mode")
    
    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "request_id": "req_123456789",
                "client_info": {
                    "user_agent": "OME-Client/1.0",
                    "version": "1.0.0"
                },
                "quality_level": "professional",
                "strict_mode": False
            }
        },
    )


class BaseAPIResponse(BaseModel):
    """Base class for all API responses with standardized fields."""
    
    # Required fields
    status: APIStatus = Field(..., description="Response status")
    message: str = Field(..., description="Human-readable response message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    
    # Optional fields
    request_id: Optional[str] = Field(None, description="Request identifier if provided")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data payload")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional response metadata")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "data": {},
                "metadata": {}
            }
        },
    )


class ErrorDetail(BaseModel):
    """Detailed error information for API responses."""
    
    code: ErrorCode = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field that caused the error")
    value: Optional[Any] = Field(None, description="Value that caused the error")
    suggestion: Optional[str] = Field(None, description="Suggested fix for the error")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input format",
                "field": "email",
                "value": "invalid-email",
                "suggestion": "Please provide a valid email address"
            }
        },
    )


class ErrorResponse(BaseAPIResponse):
    """Standardized error response format."""
    
    status: APIStatus = Field(APIStatus.ERROR, description="Error status")
    errors: List[ErrorDetail] = Field(..., description="List of error details")
    error_count: int = Field(..., description="Total number of errors")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "status": "error",
                "message": "Request validation failed",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "errors": [
                    {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid input format",
                        "field": "email",
                        "value": "invalid-email",
                        "suggestion": "Please provide a valid email address"
                    }
                ],
                "error_count": 1,
                "data": None,
                "metadata": {}
            }
        },
    )


class SuccessResponse(BaseAPIResponse):
    """Standardized success response format."""
    
    status: APIStatus = Field(APIStatus.SUCCESS, description="Success status")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "data": {},
                "metadata": {}
            }
        },
    )


class PaginationParams(BaseModel):
    """Standard pagination parameters for list endpoints."""
    
    page: int = Field(1, ge=1, description="Page number (1-based)")
    page_size: int = Field(20, ge=1, le=100, description="Number of items per page")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Optional[str] = Field("asc", pattern="^(asc|desc)$", description="Sort order")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "page_size": 20,
                "sort_by": "created_at",
                "sort_order": "desc"
            }
        },
    )


class PaginationInfo(BaseModel):
    """Pagination information for list responses."""
    
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "page_size": 20,
                "total_items": 100,
                "total_pages": 5,
                "has_next": True,
                "has_previous": False
            }
        },
    )


class PaginatedResponse(BaseAPIResponse):
    """Standardized paginated response format."""
    
    status: APIStatus = Field(APIStatus.SUCCESS, description="Success status")
    pagination: PaginationInfo = Field(..., description="Pagination information")
    items: List[Dict[str, Any]] = Field(..., description="List of items")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Items retrieved successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total_items": 100,
                    "total_pages": 5,
                    "has_next": True,
                    "has_previous": False
                },
                "items": [],
                "metadata": {}
            }
        },
    )


class LLMRequestMixin(BaseModel):
    """Mixin for requests that support LLM integration."""
    
    use_llm: Optional[bool] = Field(False, description="Enable LLM processing for this request")
    llm_provider: Optional[str] = Field(None, description="Specific LLM provider to use")
    llm_model: Optional[str] = Field(None, description="Specific LLM model to use")
    llm_temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="LLM temperature setting")
    llm_max_tokens: Optional[int] = Field(None, ge=1, le=4096, description="Maximum tokens for LLM response")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "use_llm": True,
                "llm_provider": "anthropic",
                "llm_model": "claude-sonnet-4-5",
                "llm_temperature": 0.7,
                "llm_max_tokens": 2048
            }
        },
    )


class LLMResponseMixin(BaseModel):
    """Mixin for responses that include LLM processing information."""
    
    llm_used: Optional[bool] = Field(None, description="Whether LLM was used for this response")
    llm_provider: Optional[str] = Field(None, description="LLM provider that was used")
    llm_model: Optional[str] = Field(None, description="LLM model that was used")
    llm_cost: Optional[float] = Field(None, description="Cost of LLM processing")
    llm_tokens_used: Optional[int] = Field(None, description="Number of tokens used")
    llm_processing_time: Optional[float] = Field(None, description="LLM processing time in seconds")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "llm_used": True,
                "llm_provider": "anthropic",
                "llm_model": "claude-sonnet-4-5",
                "llm_cost": 0.012,
                "llm_tokens_used": 1500,
                "llm_processing_time": 2.5
            }
        },
    )


class RequirementsInput(BaseModel):
    """Standardized input for requirements."""
    
    content: Union[str, Dict[str, Any]] = Field(..., description="Requirements content")
    type: str = Field(..., description="Type of requirements (e.g., 'okh', 'recipe', 'specification')")
    format: Optional[str] = Field(None, description="Content format (e.g., 'json', 'yaml', 'text')")
    source: Optional[str] = Field(None, description="Source of the requirements")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": {"title": "Test OKH", "version": "1.0.0"},
                "type": "okh",
                "format": "json",
                "source": "github.com/example/project"
            }
        },
    )


class CapabilitiesInput(BaseModel):
    """Standardized input for capabilities."""
    
    content: Union[str, Dict[str, Any]] = Field(..., description="Capabilities content")
    type: str = Field(..., description="Type of capabilities (e.g., 'okw', 'facility', 'equipment')")
    format: Optional[str] = Field(None, description="Content format (e.g., 'json', 'yaml', 'text')")
    source: Optional[str] = Field(None, description="Source of the capabilities")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": {"name": "Test Facility", "processes": ["assembly", "testing"]},
                "type": "okw",
                "format": "json",
                "source": "facility-registry.org"
            }
        },
    )


class ValidationResult(BaseModel):
    """Standardized validation result."""
    
    is_valid: bool = Field(..., description="Whether the content is valid")
    score: float = Field(..., ge=0.0, le=1.0, description="Validation score (0.0 to 1.0)")
    errors: List[ErrorDetail] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_valid": True,
                "score": 0.95,
                "errors": [],
                "warnings": ["Missing optional field: description"],
                "suggestions": ["Consider adding a description for better documentation"]
            }
        },
    )


class ProcessingMetrics(BaseModel):
    """Standardized processing metrics."""
    
    processing_time: float = Field(..., description="Total processing time in seconds")
    memory_used: Optional[int] = Field(None, description="Memory used in bytes")
    cpu_usage: Optional[float] = Field(None, description="CPU usage percentage")
    api_calls: Optional[int] = Field(None, description="Number of API calls made")
    cache_hits: Optional[int] = Field(None, description="Number of cache hits")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "processing_time": 1.25,
                "memory_used": 1024000,
                "cpu_usage": 15.5,
                "api_calls": 3,
                "cache_hits": 1
            }
        },
    )