from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from ....models.supply_trees import SupplyTree

class SupplyTreeSummary(BaseModel):
    """Simplified supply tree for API responses (without NetworkX graphs)"""
    id: str
    name: str
    description: Optional[str] = None
    node_count: int
    edge_count: int
    total_cost: Optional[float] = None
    estimated_time: Optional[str] = None
    facilities: List[str] = Field(default_factory=list, description="List of facility IDs used")
    
    @classmethod
    def from_supply_tree(cls, tree: 'SupplyTree') -> 'SupplyTreeSummary':
        """Create a summary from a full SupplyTree"""
        return cls(
            id=str(tree.id),
            name=tree.name,
            description=tree.description,
            node_count=len(tree.workflow.graph.nodes) if tree.workflow and tree.workflow.graph else 0,
            edge_count=len(tree.workflow.graph.edges) if tree.workflow and tree.workflow.graph else 0,
            total_cost=getattr(tree, 'total_cost', None),
            estimated_time=getattr(tree, 'estimated_time', None),
            facilities=[str(facility_id) for facility_id in getattr(tree, 'facilities', [])]
        )

class MatchResponse(BaseModel):
    """Response model for matching requirements to capabilities"""
    # Required fields first
    solutions: List[Dict[str, Any]] = Field(
        description="List of matching solutions with supply trees and scores"
    )
    
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