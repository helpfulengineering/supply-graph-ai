from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from ....models.okh import OKHManifest

class OptimizationCriteria(BaseModel):
    """Model for optimization criteria"""
    # Required fields first
    priority: str  # "cost", "time", "quality"
    
    # Optional fields after
    weights: Dict[str, float] = Field(default_factory=dict)

class MatchRequest(BaseModel):
    """Request model for matching requirements to capabilities"""
    # Optional fields - either okh_id, okh_manifest, or okh_url must be provided
    okh_id: Optional[UUID] = None
    okh_manifest: Optional[OKHManifest] = None
    okh_url: Optional[str] = Field(None, description="URL to fetch OKH manifest from")
    
    # Optional fields after
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