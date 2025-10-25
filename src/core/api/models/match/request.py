from pydantic import BaseModel, Field, model_validator
from typing import Dict, List, Optional, Any
from uuid import UUID

from ....models.okh import OKHManifest
from ..base import BaseAPIRequest, LLMRequestMixin

class OptimizationCriteria(BaseModel):
    """Model for optimization criteria"""
    # Required fields first
    priority: str  # "cost", "time", "quality"
    
    # Optional fields after
    weights: Dict[str, float] = Field(default_factory=dict)

class MatchRequest(BaseAPIRequest, LLMRequestMixin):
    """Consolidated match request with standardized fields and LLM support"""
    # Core matching fields - either okh_id, okh_manifest, or okh_url must be provided
    okh_id: Optional[UUID] = None
    okh_manifest: Optional[dict] = None  # Changed from OKHManifest to dict for API compatibility
    okh_url: Optional[str] = Field(None, description="URL to fetch OKH manifest from")
    
    # Enhanced filtering options
    access_type: Optional[str] = None
    facility_status: Optional[str] = None
    location: Optional[str] = None
    capabilities: Optional[List[str]] = None
    materials: Optional[List[str]] = None
    
    # Advanced filtering parameters
    max_distance_km: Optional[float] = None  # Distance filter
    deadline: Optional[str] = None           # Timeline filter (ISO datetime string)
    max_cost: Optional[float] = None         # Budget filter
    min_capacity: Optional[int] = None       # Capacity filter
    location_coords: Optional[Dict[str, float]] = None  # {"lat": 0.0, "lng": 0.0}
    
    # Quality and validation options
    min_confidence: Optional[float] = 0.7
    max_results: Optional[int] = 10
    
    # Backward compatibility
    include_workflows: Optional[bool] = False  # Feature flag for workflow inclusion
    
    # Legacy fields for backward compatibility
    optimization_criteria: Optional[Dict[str, float]] = Field(
        default_factory=dict,
        description="Optional weights for different optimization criteria"
    )
    okw_filters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional filters for OKW facilities (e.g., location, capabilities)"
    )
    okw_facilities: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Optional list of OKW facilities (as dicts) to use instead of loading from storage"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "okh_manifest": {
                    "title": "Test OKH Manifest",
                    "version": "1.0.0",
                    "manufacturing_specs": {
                        "process_requirements": [
                            {"process_name": "PCB Assembly", "parameters": {}}
                        ]
                    }
                },
                "access_type": "public",
                "facility_status": "active",
                "min_confidence": 0.8,
                "max_results": 5,
                "max_distance_km": 50.0,
                "deadline": "2024-12-31T23:59:59Z",
                "max_cost": 10000.0,
                "min_capacity": 100,
                "location_coords": {"lat": 37.7749, "lng": -122.4194},
                "include_workflows": False,
                "use_llm": True,
                "llm_provider": "anthropic",
                "llm_model": "claude-3-sonnet",
                "quality_level": "professional",
                "strict_mode": False
            }
        }

    @model_validator(mode='after')
    def validate_okh_input(self):
        """Ensure only one of okh_id, okh_manifest, or okh_url is provided"""
        provided_fields = []
        if self.okh_id is not None:
            provided_fields.append('okh_id')
        if self.okh_manifest is not None:
            provided_fields.append('okh_manifest')
        if self.okh_url is not None:
            provided_fields.append('okh_url')
        
        if len(provided_fields) > 1:
            raise ValueError(f"Cannot provide multiple OKH inputs: {', '.join(provided_fields)}")
        if len(provided_fields) == 0:
            raise ValueError("Must provide either okh_id, okh_manifest, or okh_url")
        return self

class ValidateMatchRequest(BaseModel):
    """Request model for validating an existing supply tree"""
    # Required fields first
    okh_id: UUID
    supply_tree_id: UUID
    
    # Optional fields after
    validation_criteria: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional criteria for validation"
    )

class SimulationParameters(BaseModel):
    """Parameters for simulation"""
    # Required fields first
    start_time: str
    
    # Optional fields after
    resource_availability: Dict[str, Any] = Field(default_factory=dict)

class SimulateRequest(BaseModel):
    """Request model for simulating execution of a supply tree"""
    # Required fields first
    supply_tree: Dict[str, Any]
    parameters: SimulationParameters