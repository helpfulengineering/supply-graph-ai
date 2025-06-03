from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from ...models.supply_trees import SupplyTree

class MatchResponse(BaseModel):
    """Response model for matching requirements to capabilities"""
    # Required fields first
    supply_trees: List[SupplyTree]
    confidence: float
    
    # Optional fields after
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the matching process"
    )

class ValidationResult(BaseModel):
    """Response model for validation results"""
    # Required fields first
    valid: bool
    confidence: float
    
    # Optional fields after
    issues: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of validation issues if any"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the validation process"
    )

class SimulationResult(BaseModel):
    """Response model for simulation results"""
    # Required fields first
    success: bool
    completion_time: str
    
    # Optional fields after
    critical_path: List[Dict[str, Any]] = []
    bottlenecks: List[Dict[str, Any]] = []
    resource_utilization: Dict[str, Any] = {}