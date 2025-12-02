"""
Context models for validation API.

This module provides Pydantic models for validation contexts.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional


class ValidationContextModel(BaseModel):
    """API model for validation context"""

    name: str = Field(..., description="Context name")
    domain: str = Field(..., description="Domain name")
    quality_level: str = Field(..., description="Quality level")
    strict_mode: bool = Field(False, description="Whether strict mode is enabled")
    validation_rules: Dict[str, Any] = Field(
        default_factory=dict, description="Validation rules for this context"
    )
    supported_types: List[str] = Field(
        default_factory=list, description="Supported validation types"
    )
    validation_strictness: Optional[str] = Field(
        None, description="Validation strictness level"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "manufacturing_professional",
                "domain": "manufacturing",
                "quality_level": "professional",
                "strict_mode": False,
                "validation_rules": {
                    "required_fields": ["title", "version", "license", "function"],
                    "validation_strictness": "standard",
                },
                "supported_types": ["okh", "okw"],
                "validation_strictness": "standard",
            }
        }
    )
