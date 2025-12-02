"""
Request models for validation API endpoints.

This module provides Pydantic models for validation requests.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, Optional


class ValidationRequest(BaseModel):
    """Request model for validation operations"""

    content: Dict[str, Any] = Field(..., description="Data to validate")
    validation_type: str = Field(..., description="Type of validation to perform")
    context: Optional[str] = Field(
        None, description="Validation context (e.g., 'manufacturing', 'hobby')"
    )
    quality_level: Optional[str] = Field(
        "professional", description="Quality level (hobby, professional, medical)"
    )
    strict_mode: Optional[bool] = Field(
        False, description="Enable strict validation mode"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": {
                    "title": "Test OKH Manifest",
                    "version": "1.0.0",
                    "license": "MIT",
                },
                "validation_type": "okh_manifest",
                "context": "manufacturing",
                "quality_level": "professional",
                "strict_mode": False,
            }
        }
    )


class ValidationContextRequest(BaseModel):
    """Request model for validation context operations"""

    domain: str = Field(..., description="Domain name")
    quality_level: Optional[str] = Field("professional", description="Quality level")
    strict_mode: Optional[bool] = Field(
        False, description="Enable strict validation mode"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "domain": "manufacturing",
                "quality_level": "professional",
                "strict_mode": False,
            }
        }
    )
