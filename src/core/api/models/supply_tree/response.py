from datetime import datetime
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


# ---------------------------------------------------------------------------
# Saved-solution routes (#373)
#
# Every model below is derived from a golden captured in
# ``tests/integration/test_supply_tree_solution_contract.py``, not from reading
# the handlers. ``response_model`` filters undeclared fields, so a model
# written from the code rather than the payload silently drops whatever the
# code does not obviously return — which is how #369's two bugs got in.
# ---------------------------------------------------------------------------


class SolutionListRow(BaseModel):
    """One row of the solutions listing.

    Every field is optional because every field is read with ``.get()`` from a
    sidecar metadata object that predates most of them. A solution written
    before ``okh_title`` existed has no ``okh_title``, and declaring it
    required would turn one legacy row into a 500 for the whole listing.
    """

    id: Optional[str] = None
    okh_id: Optional[str] = None
    okh_title: Optional[str] = None
    facility_name: Optional[str] = None
    matching_mode: Optional[str] = None
    tree_count: Optional[int] = None
    component_count: Optional[int] = None
    facility_count: Optional[int] = None
    score: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    expires_at: Optional[str] = None
    ttl_days: Optional[int] = None
    tags: List[str] = []
    # A real ``datetime``, unlike its neighbours: the other timestamps are
    # strings read back out of a JSON sidecar, while this one comes off the
    # storage object itself. Typing it ``str`` makes the whole listing 500.
    last_modified: Optional[datetime] = None
    age_days: Optional[int] = None


class SolutionListData(BaseModel):
    """The ``data`` payload of the solutions listing."""

    result: List[SolutionListRow]


class SolutionListResponse(SuccessResponse):
    """Envelope for ``GET /api/supply-tree/solutions``."""

    data: SolutionListData


class SolutionValidationResult(BaseModel):
    """Validation attached to a nested solution."""

    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    unmatched_components: List[str] = []
    circular_dependencies: List[List[str]] = []
    missing_dependencies: List[str] = []


class SolutionDetailData(BaseModel):
    """A stored solution, as ``SupplyTreeSolution.to_dict`` serialises it.

    The optional fields are not stylistic: ``to_dict`` emits ``tree`` only when
    the solution holds exactly one tree, and the nested block only when those
    attributes are set. A model declaring them required would reject a
    single-level solution; one omitting them would filter them off a nested
    one. The contract test captures both branches for exactly this reason.
    """

    # Free-form on purpose. These are ``SupplyTree.to_dict()`` payloads, and a
    # strict model here would silently filter any field that dict grows —
    # reintroducing the drift this model exists to prevent, one level down.
    all_trees: List[Dict[str, Any]]
    root_trees: Optional[List[Dict[str, Any]]] = None
    tree: Optional[Dict[str, Any]] = None

    score: float
    metrics: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    is_nested: bool = False

    component_mapping: Optional[Dict[str, List[Dict[str, Any]]]] = None
    dependency_graph: Optional[Dict[str, List[str]]] = None
    production_sequence: Optional[List[List[str]]] = None
    validation_result: Optional[SolutionValidationResult] = None
    total_estimated_cost: Optional[float] = None
    total_estimated_time: Optional[str] = None


class SolutionDetailResponse(SuccessResponse):
    """Envelope for ``GET /api/supply-tree/solution/{solution_id}``."""

    data: SolutionDetailData


class SolutionStalenessData(BaseModel):
    """Whether a saved solution has gone stale, and how old it is."""

    is_stale: bool
    staleness_reason: Optional[str] = None
    age_days: Optional[int] = None
    solution_id: str


class SolutionStalenessResponse(SuccessResponse):
    """Envelope for ``GET /api/supply-tree/solution/{id}/staleness``."""

    data: SolutionStalenessData


class SolutionExtendData(BaseModel):
    """Result of extending a solution's time-to-live."""

    extended: bool
    solution_id: str
    additional_days: int


class SolutionExtendResponse(SuccessResponse):
    """Envelope for ``POST /api/supply-tree/solution/{id}/extend``."""

    data: SolutionExtendData


class SolutionDeleteData(BaseModel):
    """Result of deleting a saved solution."""

    deleted: bool
    solution_id: str


class SolutionDeleteResponse(SuccessResponse):
    """Envelope for ``DELETE /api/supply-tree/solution/{solution_id}``."""

    data: SolutionDeleteData


class VisualizationNode(BaseModel):
    """One tree, as a node in the visualization graph."""

    id: str
    label: str
    component_id: Optional[str] = None
    facility_name: Optional[str] = None
    depth: int
    production_stage: str
    confidence_score: float
    estimated_cost: Optional[float] = None
    estimated_time: Optional[str] = None


class VisualizationEdge(BaseModel):
    """A relationship between two trees.

    Only nested solutions produce these — an edge exists where a tree has a
    parent or a dependency — so the golden for this shape comes from a nested
    fixture rather than from a match.
    """

    source: str
    target: str
    type: str


class VisualizationResourceCost(BaseModel):
    """Roll-up of cost and time across the solution."""

    total_estimated_cost: Optional[float] = None
    total_estimated_time: Optional[str] = None


class VisualizationSupplyTree(BaseModel):
    """The graph itself: nodes, edges and the orderings derived from them."""

    solution_id: str
    nodes: List[VisualizationNode]
    edges: List[VisualizationEdge]
    dependency_graph: Dict[str, List[str]]
    production_sequence: List[List[str]]
    resource_cost: VisualizationResourceCost


class VisualizationMatchingOverview(BaseModel):
    """How the solution was arrived at."""

    matching_mode: str
    score: float
    tree_count: int


class VisualizationMatching(BaseModel):
    """Matching context carried alongside the graph."""

    overview: VisualizationMatchingOverview


class FacilityDistributionEntry(BaseModel):
    """How many trees a given facility accounts for."""

    facility_name: str
    tree_count: int


class VisualizationRouteHints(BaseModel):
    """Placeholder for transport routing, which the contract does not carry."""

    status: str
    note: str


class VisualizationNetwork(BaseModel):
    """Facility-level view of the solution."""

    facility_distribution: List[FacilityDistributionEntry]
    route_hints: VisualizationRouteHints


class VisualizationKPIs(BaseModel):
    """The four counters the dashboard shows above the graph."""

    tree_count: int
    edge_count: int
    stage_count: int
    solution_score: float


class VisualizationDashboard(BaseModel):
    """Dashboard block of the bundle."""

    kpis: VisualizationKPIs


class VisualizationArtifacts(BaseModel):
    """What else can be fetched for this solution, and from where."""

    graphml_endpoint: str
    json_bundle: bool
    html_report: bool


class VisualizationBundleData(BaseModel):
    """The ``data`` payload of the visualization-bundle route."""

    schema_version: str
    source_type: str
    generated_at: str
    matching: VisualizationMatching
    supply_tree: VisualizationSupplyTree
    network: VisualizationNetwork
    dashboard: VisualizationDashboard
    artifacts: VisualizationArtifacts


class SolutionVisualizationResponse(SuccessResponse):
    """Envelope for ``GET /api/supply-tree/solution/{id}/visualization``."""

    data: VisualizationBundleData
