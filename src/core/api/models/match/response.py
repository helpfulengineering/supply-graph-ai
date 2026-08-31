from typing import TYPE_CHECKING, Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from ..base import LLMResponseMixin, SuccessResponse
from ..base import ValidationResult as BaseValidationResult

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
    facilities: List[str] = Field(
        default_factory=list, description="List of facility IDs used"
    )

    @classmethod
    def from_supply_tree(cls, tree: "SupplyTree") -> "SupplyTreeSummary":
        """Create a summary from a full SupplyTree"""
        name = tree.metadata.get("okh_title", f"Supply Tree {str(tree.id)[:8]}")
        description = tree.metadata.get(
            "description",
            f'Manufacturing solution for {tree.metadata.get("okh_title", "hardware project")}',
        )
        total_nodes = sum(
            len(workflow.graph.nodes) for workflow in tree.workflows.values()
        )
        total_edges = sum(
            len(workflow.graph.edges) for workflow in tree.workflows.values()
        )

        return cls(
            id=str(tree.id),
            name=name,
            description=description,
            node_count=total_nodes,
            edge_count=total_edges,
            total_cost=getattr(tree, "total_cost", None),
            estimated_time=getattr(tree, "estimated_time", None),
            facilities=[
                str(facility_id) for facility_id in getattr(tree, "facilities", [])
            ],
        )


class MatchResponse(SuccessResponse, LLMResponseMixin):
    """Consolidated match response with standardized fields and LLM information"""

    model_config = ConfigDict(
        json_schema_extra={
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
                        "match_type": "direct",
                    }
                ],
                "total_solutions": 1,
                "processing_time": 2.5,
                "matching_metrics": {
                    "direct_matches": 1,
                    "heuristic_matches": 0,
                    "nlp_matches": 0,
                },
                "validation_results": [],
                "status": "success",
                "message": "Matching completed successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "llm_used": True,
                "llm_provider": "anthropic",
                "llm_cost": 0.025,
                "data": {},
            }
        }
    )

    solutions: List[dict] = []
    total_solutions: int = 0
    processing_time: float = 0.0
    matching_metrics: Optional[dict] = None
    validation_results: Optional[List[BaseValidationResult]] = None
    match_summary: Optional[Dict[str, Any]] = None
    coverage_gaps: Optional[List[str]] = None
    match_summary_text: Optional[str] = None
    suggestions: Optional[List[str]] = None
    suggestion_codes: Optional[List[str]] = None
    human_summary: Optional[Dict[str, Any]] = None


class ValidationResult(BaseModel):
    """Response model for validation results"""

    valid: bool
    confidence: float
    issues: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of validation issues if any"
    )


class SimulateResponse(SuccessResponse):
    """Response model for simulation results"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Simulation completed successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "completion_time": "2023-01-10T15:30:00Z",
                "critical_path": [
                    {"step": "material_preparation", "duration": "2 days"},
                    {"step": "assembly", "duration": "5 days"},
                ],
                "bottlenecks": [
                    {"resource": "CNC Machine", "utilization": 0.95, "impact": "high"}
                ],
                "resource_utilization": {
                    "equipment": {"CNC Machine": 0.95, "3D Printer": 0.60},
                    "labor": {"technicians": 0.80},
                },
            }
        }
    )

    completion_time: str = Field(
        ..., description="Estimated completion time (ISO format)"
    )

    critical_path: List[Dict[str, Any]] = Field(
        default_factory=list, description="Critical path in the supply tree"
    )
    bottlenecks: List[Dict[str, Any]] = Field(
        default_factory=list, description="Identified bottlenecks"
    )
    resource_utilization: Dict[str, Any] = Field(
        default_factory=dict, description="Resource utilization metrics"
    )


class SimulationResult(BaseModel):
    """Response model for simulation results"""

    success: bool
    completion_time: str
    critical_path: List[Dict[str, Any]] = []
    bottlenecks: List[Dict[str, Any]] = []
    resource_utilization: Dict[str, Any] = {}


class FacilityDesignMatch(BaseModel):
    """One design a facility could make, as the reverse matcher ranks them.

    Frozen from a populated payload rather than from reading the code: the
    golden in ``tests/api/golden/match_facility_shape.json`` captured an empty
    list for as long as the fixture design was invisible to matching, so this
    model could not honestly be written until that was fixed (#402). Declaring
    it from the source would have risked filtering a field never seen on the
    wire, which is the failure the whole convention exists to prevent.
    """

    okh_id: str
    okh_title: Optional[str] = None
    #: 0..1, the matcher's own score.
    confidence: float
    #: 1-based position in the returned ordering.
    rank: int


class FacilityDesignsData(BaseModel):
    """The ``data`` payload of POST /api/match/facility — reverse matching.

    Derived from the payload captured in
    ``tests/api/golden/match_facility_shape.json`` before this model existed.
    """

    okw_id: str
    facility_name: Optional[str]
    designs: List[FacilityDesignMatch]
    total_designs: int
    #: How many manifests were examined to produce `designs`.
    designs_considered: int
    processing_time: float


class FacilityDesignsResponse(SuccessResponse):
    data: FacilityDesignsData


# ---------------------------------------------------------------------------
# POST /api/match — the two branches (#373)
#
# Derived from the four goldens in
# ``tests/integration/test_match_contract.py``. The endpoint answers with two
# structurally different payloads chosen by ``matching_mode``, so this is a
# union discriminated on that field: one flat model would filter whichever
# branch it is not.
# ---------------------------------------------------------------------------


class MatchSummary(BaseModel):
    """Process coverage for a match, the same shape in both branches."""

    matching_mode: str
    solution_count: int
    required_process_count: int
    covered_process_count: int
    coverage_ratio: float
    # Keyed by process name, so a map rather than a fixed shape.
    coverage_gap_counts: Dict[str, int] = Field(default_factory=dict)
    facility_combination_requested: bool
    facility_combination_applied: bool
    max_facilities_per_solution: int
    return_alternative_solutions: bool
    combination_strategy: str
    warnings: List[str] = Field(default_factory=list)


class MatchingMetrics(BaseModel):
    """Which matching layer produced the results."""

    direct_matches: int
    heuristic_matches: int
    nlp_matches: int
    llm_matches: int


class _MatchDataBase(BaseModel):
    """What both branches carry.

    The three optional fields are conditional on the request, not on the
    branch: ``solution_id`` is written only when ``save_solution`` was asked
    for — and it is the only way a caller learns where its result went, so
    omitting it here would silently lose it — while ``human_summary`` and
    ``save_warning`` appear only when generated or when a save failed.
    """

    processing_time: float
    match_summary: MatchSummary
    match_summary_text: str
    coverage_gaps: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    suggestion_codes: List[str] = Field(default_factory=list)

    solution_id: Optional[str] = None
    human_summary: Optional[Dict[str, Any]] = None
    save_warning: Optional[str] = None


class SingleLevelMatchData(_MatchDataBase):
    """One facility per solution, ranked. The default branch."""

    matching_mode: Literal["single-level"]
    total_solutions: int
    matching_metrics: MatchingMetrics
    applied_filters: Dict[str, Any] = Field(default_factory=dict)
    validation_results: List[Dict[str, Any]] = Field(default_factory=list)

    # Free-form on purpose. Each item carries a facility projection, a
    # SupplyTree.to_dict() and — only when include_explanation was requested —
    # `explanation` and `explanation_human`, which the UI reads. A strict model
    # would filter whichever of those the request did not ask for, which is the
    # drift this convention exists to prevent, one level down.
    solutions: List[Dict[str, Any]] = Field(default_factory=list)


class NestedMatchData(_MatchDataBase):
    """One solution spanning several facilities, with a component hierarchy."""

    matching_mode: Literal["nested"]

    # Free-form for the same reason as `solutions` above: this is a
    # SupplyTreeSolution.to_dict(), whose optional keys come and go with how
    # the solution was built.
    solution: Dict[str, Any] = Field(default_factory=dict)
    validation_result: Optional[Dict[str, Any]] = None


MatchData = Annotated[
    Union[SingleLevelMatchData, NestedMatchData],
    Field(discriminator="matching_mode"),
]


class MatchRunResponse(SuccessResponse):
    """Envelope for ``POST /api/match``.

    ``data`` is the discriminated union, so the branch a caller got is a typed
    fact rather than something to infer from which keys happen to be present.
    """

    data: MatchData
