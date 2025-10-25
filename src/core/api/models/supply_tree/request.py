from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from uuid import UUID

# Import base classes for enhanced functionality
from ..base import BaseAPIRequest, LLMRequestMixin

class SupplyTreeCreateRequest(BaseAPIRequest, LLMRequestMixin):
    """Consolidated supply tree creation request with standardized fields and LLM support"""
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
    
    class Config:
        json_schema_extra = {
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
                "llm_model": "claude-3-sonnet",
                "quality_level": "professional",
                "strict_mode": False
            }
        }


class SupplyTreeOptimizeRequest(BaseModel):
    """Request model for optimizing a supply tree"""
    # Required fields only
    criteria: Dict[str, Any]

class SupplyTreeValidateRequest(BaseModel):
    """Request model for validating a supply tree"""
    # Optional fields
    okh_reference: Optional[str] = None
    okw_references: Optional[List[str]] = None