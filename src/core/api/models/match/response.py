from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from ..base import SuccessResponse, LLMResponseMixin, ValidationResult as BaseValidationResult

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

class MatchResponse(SuccessResponse, LLMResponseMixin):
    """Consolidated match response with standardized fields and LLM information"""
    # Core response data
    solutions: List[dict] = []
    total_solutions: int = 0
    processing_time: float = 0.0
    
    # Enhanced metadata
    matching_metrics: Optional[dict] = None
    validation_results: Optional[List[BaseValidationResult]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "solutions": [
                    {
                        "id": "00000000-0000-0000-0000-000000000000",
                        "facility_id": "12345678-1234-1234-1234-123456789012",
                        "facility_name": "Electronics Manufacturing Facility",
                        "okh_reference": "electronics-manufacturing",
                        "confidence_score": 0.8,
                        "estimated_cost": 1000.0,
                        "estimated_time": "2 weeks",
                        "materials_required": ["copper", "plastic", "silicon"],
                        "capabilities_used": ["soldering", "assembly", "testing"],
                        "match_type": "direct"
                    }
                ],
                "total_solutions": 1,
                "processing_time": 2.5,
                "matching_metrics": {
                    "direct_matches": 1,
                    "heuristic_matches": 0,
                    "nlp_matches": 0
                },
                "validation_results": [],
                "status": "success",
                "message": "Matching completed successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "llm_used": True,
                "llm_provider": "anthropic",
                "llm_cost": 0.025,
                "data": {}
            }
        }

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