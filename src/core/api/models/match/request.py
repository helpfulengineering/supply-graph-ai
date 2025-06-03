from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from ...models.okh import OKHManifest

class OptimizationCriteria(BaseModel):
    """Model for optimization criteria"""
    # Required fields first
    priority: str  # "cost", "time", "quality"
    
    # Optional fields after
    weights: Dict[str, float] = Field(default_factory=dict)

class MatchRequest(BaseModel):
    """Request model for matching requirements to capabilities"""
    # Optional fields - either okh_id or okh_manifest must be provided
    okh_id: Optional[UUID] = None
    okh_manifest: Optional[OKHManifest] = None
    
    # Optional fields after
    optimization_criteria: Optional[Dict[str, float]] = Field(
        default_factory=dict,
        description="Optional weights for different optimization criteria"
    )

    @validator('okh_id', 'okh_manifest')
    def validate_okh_input(cls, v, values):
        """Ensure either okh_id or okh_manifest is provided, but not both"""
        if 'okh_id' in values and values['okh_id'] is not None and v is not None:
            raise ValueError("Cannot provide both okh_id and okh_manifest")
        return v

    @validator('okh_manifest')
    def validate_okh_manifest(cls, v, values):
        """Ensure at least one of okh_id or okh_manifest is provided"""
        if v is None and values.get('okh_id') is None:
            raise ValueError("Must provide either okh_id or okh_manifest")
        return v

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