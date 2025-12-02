from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..base import (
    LLMResponseMixin,
    SuccessResponse,
)
from ..base import ValidationResult as BaseValidationResult


class PackageResponse(SuccessResponse, LLMResponseMixin):
    """Response model for package operations with standardized fields and LLM information"""

    # Core response data
    package: Optional[dict] = None
    processing_time: float = 0.0

    # Enhanced metadata
    validation_results: Optional[List[BaseValidationResult]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Package operation completed successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "package": {
                    "name": "test-package",
                    "version": "1.0.0",
                    "status": "built",
                },
                "processing_time": 2.5,
                "llm_used": True,
                "llm_provider": "anthropic",
                "llm_cost": 0.025,
                "data": {},
                "metadata": {},
            }
        }
    )


class PackageMetadataResponse(BaseModel):
    """Response model for package metadata"""

    # Required fields
    name: str
    version: str
    package_path: str

    # Optional fields
    created_at: Optional[str] = None
    size: Optional[int] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PackageListResponse(BaseModel):
    """Response model for listing packages"""

    # Required fields
    packages: List[PackageMetadataResponse]
    total: int
    page: int
    page_size: int


class PackageVerificationResponse(BaseModel):
    """Response model for package verification"""

    # Required fields
    valid: bool
    checksum_match: bool

    # Optional fields
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PackagePushResponse(BaseModel):
    """Response model for package push operations"""

    # Required fields
    success: bool
    message: str

    # Optional fields
    remote_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PackagePullResponse(BaseModel):
    """Response model for package pull operations"""

    # Required fields
    success: bool
    message: str

    # Optional fields
    local_path: Optional[str] = None
    metadata: Optional[PackageMetadataResponse] = None
