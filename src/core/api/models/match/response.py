from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, TYPE_CHECKING


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
        # Get name and description from metadata or use defaults
        name = tree.metadata.get('okh_title', f'Supply Tree {str(tree.id)[:8]}')
        description = tree.metadata.get('description', f'Manufacturing solution for {tree.metadata.get("okh_title", "hardware project")}')
        
        # Calculate node and edge counts from workflows
        total_nodes = sum(len(workflow.graph.nodes) for workflow in tree.workflows.values())
        total_edges = sum(len(workflow.graph.edges) for workflow in tree.workflows.values())
        
        return cls(
            id=str(tree.id),
            name=name,
            description=description,
            node_count=total_nodes,
            edge_count=total_edges,
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