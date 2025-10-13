"""
Response models for validation API endpoints.

This module provides Pydantic models for validation responses.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from .context import ValidationContextModel


class ValidationIssue(BaseModel):
    """Model for validation issues"""
    severity: str = Field(..., description="Issue severity: error, warning, or info")
    message: str = Field(..., description="Issue message")
    path: List[str] = Field(default_factory=list, description="Path to the field with the issue")
    code: Optional[str] = Field(None, description="Issue code for programmatic handling")
    
    class Config:
        json_schema_extra = {
            "example": {
                "severity": "error",
                "message": "Required field 'title' is missing",
                "path": ["title"],
                "code": "required_field_missing"
            }
        }


class ValidationResponse(BaseModel):
    """Response model for validation operations"""
    valid: bool = Field(..., description="Whether the validation passed")
    normalized_content: Dict[str, Any] = Field(..., description="Normalized content after validation")
    issues: Optional[List[ValidationIssue]] = Field(None, description="List of validation issues")
    context: Optional[ValidationContextModel] = Field(None, description="Validation context used")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional validation metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "valid": False,
                "normalized_content": {
                    "title": "Test OKH Manifest",
                    "version": "1.0.0",
                    "license": "MIT"
                },
                "issues": [
                    {
                        "severity": "error",
                        "message": "Required field 'function' is missing",
                        "path": ["function"],
                        "code": "required_field_missing"
                    }
                ],
                "context": {
                    "name": "manufacturing_professional",
                    "domain": "manufacturing",
                    "quality_level": "professional",
                    "strict_mode": False,
                    "validation_strictness": "standard"
                },
                "metadata": {
                    "completeness_score": 0.75,
                    "validation_time_ms": 45
                }
            }
        }


class ValidationContextResponse(BaseModel):
    """Response model for validation context operations"""
    contexts: List[ValidationContextModel] = Field(..., description="List of available validation contexts")
    total_count: int = Field(..., description="Total number of contexts")
    
    class Config:
        json_schema_extra = {
            "example": {
                "contexts": [
                    {
                        "name": "manufacturing_hobby",
                        "domain": "manufacturing",
                        "quality_level": "hobby",
                        "strict_mode": False,
                        "validation_strictness": "relaxed",
                        "validation_rules": {
                            "required_fields": ["title", "version", "license"],
                            "validation_strictness": "relaxed"
                        },
                        "supported_types": ["okh", "okw"]
                    }
                ],
                "total_count": 1
            }
        }
