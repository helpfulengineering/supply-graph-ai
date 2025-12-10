from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Import base classes for enhanced functionality
from ..base import BaseAPIRequest, LLMRequestMixin


class SupplyTreeCreateRequest(BaseAPIRequest, LLMRequestMixin):
    """Consolidated supply tree creation request with standardized fields and LLM support"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "facility_id": "12345678-1234-1234-1234-123456789012",
                "facility_name": "Electronics Manufacturing Facility",
                "okh_reference": "electronics-manufacturing",
                "confidence_score": 0.8,
                "estimated_cost": 1000.0,
                "estimated_time": "2 weeks",
                "materials_required": ["copper", "plastic", "silicon"],
                "capabilities_used": ["soldering", "assembly", "testing"],
                "match_type": "direct",
                "metadata": {"project": "IoT Sensor Node"},
                "use_llm": True,
                "llm_provider": "anthropic",
                "llm_model": "claude-sonnet-4-5",
                "quality_level": "professional",
                "strict_mode": False,
            }
        }
    )

    # Required fields first
    facility_id: UUID
    facility_name: str
    okh_reference: str
    confidence_score: float

    # Optional fields after
    estimated_cost: Optional[float] = None
    estimated_time: Optional[str] = None
    materials_required: List[str] = Field(default_factory=list)
    capabilities_used: List[str] = Field(default_factory=list)
    match_type: str = "unknown"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SupplyTreeOptimizeRequest(BaseAPIRequest):
    """Request model for optimizing a supply tree"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "criteria": {
                    "priority": "cost",  # or "time", "quality"
                    "weights": {"cost": 0.5, "time": 0.3, "quality": 0.2},
                }
            }
        }
    )

    # Required fields
    criteria: Dict[str, Any] = Field(
        ..., description="Optimization criteria with priority and weights"
    )


class SupplyTreeValidateRequest(BaseModel):
    """Request model for validating a supply tree"""

    # Optional fields
    okh_reference: Optional[str] = None
    okw_references: Optional[List[str]] = None
    domain: Optional[str] = Field(
        default="manufacturing",
        description="Domain for validation (e.g., 'manufacturing', 'cooking')",
    )
    quality_level: Optional[str] = Field(
        default="professional",
        description="Quality level: hobby, professional, or medical",
    )
    strict_mode: Optional[bool] = Field(
        default=False, description="Enable strict validation mode"
    )


class SolutionLoadRequest(BaseAPIRequest):
    """Request model for loading a supply tree solution from multiple sources"""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source": "storage",
                "solution_id": "12345678-1234-1234-1234-123456789012"
            }
        }
    )
    
    source: str = Field(
        ...,
        description="Source type: 'storage', 'file', or 'inline'"
    )
    solution_id: Optional[UUID] = Field(
        None,
        description="Solution ID (required if source='storage')"
    )
    file_path: Optional[str] = Field(
        None,
        description="Path to local solution file (required if source='file')"
    )
    solution: Optional[Dict[str, Any]] = Field(
        None,
        description="Inline solution data (required if source='inline')"
    )
    
    @model_validator(mode='after')
    def validate_source_requirements(self):
        """Validate that required fields are present based on source"""
        if self.source == "storage":
            if not self.solution_id:
                raise ValueError("solution_id is required when source='storage'")
        elif self.source == "file":
            if not self.file_path:
                raise ValueError("file_path is required when source='file'")
        elif self.source == "inline":
            if not self.solution:
                raise ValueError("solution is required when source='inline'")
        else:
            raise ValueError(f"Invalid source: {self.source}. Must be 'storage', 'file', or 'inline'")
        
        return self


class CleanupStaleSolutionsRequest(BaseAPIRequest):
    """Request model for cleaning up stale solutions"""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dry_run": True,
                "max_age_days": 45,
                "before_date": "2024-01-01T00:00:00"
            }
        }
    )
    
    dry_run: bool = Field(
        default=True,
        description="If True, preview what would be deleted without actually deleting"
    )
    max_age_days: Optional[int] = Field(
        None,
        description="Delete solutions older than N days"
    )
    before_date: Optional[str] = Field(
        None,
        description="Delete solutions created before this date (ISO format)"
    )


class ExtendSolutionTTLRequest(BaseAPIRequest):
    """Request model for extending solution TTL"""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "additional_days": 30
            }
        }
    )
    
    additional_days: int = Field(
        default=30,
        description="Number of days to add to expiration time"
    )
