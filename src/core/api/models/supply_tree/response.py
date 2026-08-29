from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# Import base classes for enhanced functionality
from ..base import LLMResponseMixin, SuccessResponse
from ..base import ValidationResult as BaseValidationResult


class SupplyTreeResponse(SuccessResponse, LLMResponseMixin):
    """Consolidated supply tree response with standardized fields and LLM information"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "00000000-0000-0000-0000-000000000000",
                "facility_id": "12345678-1234-1234-1234-123456789012",
                "facility_name": "Electronics Manufacturing Facility",
                "okh_reference": "electronics-manufacturing",
                "confidence_score": 0.8,
                "creation_time": "2024-01-01T12:00:00Z",
                "estimated_cost": 1000.0,
                "estimated_time": "2 weeks",
                "materials_required": ["copper", "plastic", "silicon"],
                "capabilities_used": ["soldering", "assembly", "testing"],
                "match_type": "direct",
                "metadata": {"project": "IoT Sensor Node"},
                "processing_time": 2.5,
                "validation_results": [],
                "status": "success",
                "message": "Supply tree operation completed successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "llm_used": True,
                "llm_provider": "anthropic",
                "llm_cost": 0.025,
                "data": {},
            }
        }
    )

    id: UUID
    facility_id: UUID
    facility_name: str
    okh_reference: str
    confidence_score: float
    creation_time: str

    estimated_cost: Optional[float] = None
    estimated_time: Optional[str] = None
    materials_required: List[str] = []
    capabilities_used: List[str] = []
    match_type: str = "unknown"
    metadata: Dict[str, Any] = {}

    processing_time: float = 0.0
    validation_results: Optional[List[BaseValidationResult]] = None


# Keep the old class name for backward compatibility
SimplifiedSupplyTreeResponse = SupplyTreeResponse


class OptimizationMetrics(BaseModel):
    """Response model for optimization metrics"""

    cost: Optional[float] = None
    time: Optional[str] = None


class SupplyTreeOptimizationResponse(SupplyTreeResponse):
    """Response model for optimized supply tree"""

    # Additional required field in this subclass
    optimization_metrics: OptimizationMetrics


class ValidationIssue(BaseModel):
    """Model for validation issues"""

    type: str  # "error", "warning", "info"
    message: str

    path: Optional[str] = None
    component: Optional[str] = None


class ValidationResult(BaseModel):
    """Response model for validation results"""

    valid: bool
    confidence: float

    issues: List[Dict[str, Any]] = []


class SupplyTreeListResponse(BaseModel):
    """Response model for listing supply trees"""

    results: List[SupplyTreeResponse]
    total: int
    page: int
    page_size: int


class HierarchyNode(BaseModel):
    """One node of the component tree, with its children inline.

    Recursive: ``children`` holds the same shape, which is how the hierarchy
    carries parent/child structure the visualization bundle does not have.
    """

    component_id: str
    component_name: str
    tree_id: str
    depth: int
    production_stage: str
    children: List["HierarchyNode"] = []


class RootComponentRef(BaseModel):
    """A top-level component — an object, not an id.

    Named explicitly because the frontend assumed this was a bare string and
    rendered it directly, which threw React #31 and took down the page (#369).
    """

    component_id: str
    component_name: str
    tree_id: str


class ComponentDetail(BaseModel):
    """Per-component summary, plus the serialised trees that produced it."""

    component_id: str
    component_name: str
    tree_count: int
    depth: int
    production_stage: str
    component_path: List[str]
    # Free-form on purpose. These are ``SupplyTree.to_dict()`` payloads, and a
    # strict model here would silently filter any field that dict grows —
    # reintroducing the drift this model exists to prevent, one level down.
    trees: List[Dict[str, Any]]


class HierarchySummary(BaseModel):
    """Counts the UI shows as KPIs above the component list."""

    total_components: int
    root_components: int
    total_trees: int
    max_depth: int


class SolutionHierarchyData(BaseModel):
    """The ``data`` payload of the component-hierarchy route."""

    hierarchy: List[HierarchyNode]
    root_components: List[RootComponentRef]
    component_details: Dict[str, ComponentDetail]
    summary: HierarchySummary


class SolutionHierarchyResponse(SuccessResponse):
    """Envelope for the component-hierarchy route.

    Declaring this is what makes ``openapi-typescript`` generate a response
    type for the route. Without it the endpoint returned a bare ``dict``, the
    generated schema said nothing, and the frontend filled the gap with a
    hand-written type that was wrong.

    ``response_model`` filters undeclared fields, so this model is frozen
    against a golden capture in
    ``tests/api/test_supply_tree_hierarchy_contract.py``.
    """

    data: SolutionHierarchyData
