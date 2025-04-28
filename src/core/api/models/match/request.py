from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

class OptimizationCriteria(BaseModel):
    """Model for optimization criteria"""
    # Required fields first
    priority: str  # "cost", "time", "quality"
    
    # Optional fields after
    weights: Dict[str, float] = Field(default_factory=dict)

class MatchRequest(BaseModel):
    """Request model for matching requirements to capabilities"""
    # Required fields first
    requirements: Dict[str, Any]
    capabilities: List[str]
    
    # Optional fields after
    context: Optional[str] = None
    optimization_criteria: Optional[OptimizationCriteria] = None

class ValidateMatchRequest(BaseModel):
    """Request model for validating an existing supply tree"""
    # Required fields first
    supply_tree: Dict[str, Any]
    
    # Optional fields after
    okh_reference: Optional[str] = None
    okw_references: Optional[List[str]] = None

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