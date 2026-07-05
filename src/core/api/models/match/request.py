from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..base import BaseAPIRequest, LLMRequestMixin


class OptimizationCriteria(BaseModel):
    """Model for optimization criteria"""

    priority: str  # "cost", "time", "quality"

    weights: Dict[str, float] = Field(default_factory=dict)


class MatchRequest(BaseAPIRequest, LLMRequestMixin):
    """Consolidated match request with standardized fields and LLM support"""

    okh_id: Optional[UUID] = None
    okh_manifest: Optional[dict] = (
        None  # Changed from OKHManifest to dict for API compatibility
    )
    okh_url: Optional[str] = Field(None, description="URL to fetch OKH manifest from")

    recipe_id: Optional[UUID] = None
    recipe: Optional[dict] = None
    recipe_url: Optional[str] = Field(None, description="URL to fetch recipe from")

    domain: Optional[str] = Field(
        None,
        description="Domain override (manufacturing, cooking). Auto-detected if not provided",
    )

    access_type: Optional[str] = None
    facility_status: Optional[str] = None
    location: Optional[str] = None
    capabilities: Optional[List[str]] = None
    materials: Optional[List[str]] = None
    max_candidate_facilities: Optional[int] = Field(
        200,
        ge=1,
        le=5000,
        description=(
            "Upper bound on facilities considered during matching after requirement-aware "
            "prefiltering. Lower values improve latency on large OKW pools."
        ),
    )

    max_distance_km: Optional[float] = None
    deadline: Optional[str] = None
    max_cost: Optional[float] = None
    min_capacity: Optional[int] = None
    location_coords: Optional[Dict[str, float]] = None  # {"lat": 0.0, "lng": 0.0}

    # Quality and validation options
    min_confidence: Optional[float] = 0.1  # Relaxed default; caller may raise as needed
    max_results: Optional[int] = 10

    # Unified depth-based matching control
    max_depth: Optional[int] = Field(
        0,  # Default: single-level matching (backward compatible)
        ge=0,
        le=10,
        description=(
            "Maximum depth for BOM explosion. "
            "0 = single-level matching (no nesting), "
            "> 0 = nested matching with specified depth. "
            "Default: 0 (single-level matching for backward compatibility)"
        ),
    )

    # Optional: Auto-detect if nested matching is needed
    auto_detect_depth: Optional[bool] = Field(
        False,
        description=(
            "Auto-detect if nested matching is needed based on OKH structure. "
            "If True and max_depth=0, will use configured default depth (from MAX_DEPTH config) "
            "when nested components detected."
        ),
    )

    include_validation: Optional[bool] = Field(
        True,
        description="Include validation results in response (for nested matching)",
    )

    include_explanation: Optional[bool] = Field(
        False,
        description="Include per-facility match explanations (which layer/rule matched each requirement).",
    )
    include_human_summary: Optional[bool] = Field(
        False,
        description=(
            "Include multi-level human-readable summaries in the response. "
            "When enabled, the API returns executive, technical, and detailed summary views."
        ),
    )
    human_summary_profile: Literal["balanced", "executive", "analyst"] = Field(
        "balanced",
        description=(
            "Role-oriented summary profile used when include_human_summary=true. "
            "'balanced' keeps the default mixed view, 'executive' favors concise business framing, "
            "and 'analyst' adds extra quantitative detail."
        ),
    )

    allow_facility_combinations: Optional[bool] = Field(
        False,
        description=(
            "Enable facility-combination matching mode for manufacturing. "
            "When enabled, the service may return aggregated multi-facility solutions "
            "instead of requiring one facility to satisfy all process requirements."
        ),
    )
    max_facilities_per_solution: Optional[int] = Field(
        3,
        ge=1,
        le=20,
        description="Maximum number of facilities allowed in a single aggregated solution.",
    )
    return_alternative_solutions: Optional[bool] = Field(
        True,
        description=(
            "If True, return multiple ranked alternatives when available. "
            "If False, return only the top-ranked solution."
        ),
    )
    combination_strategy: Optional[str] = Field(
        "greedy",
        description=(
            "Strategy identifier for facility-combination solver. "
            "Current values are forward-compatible; 'greedy' is the default."
        ),
    )

    # Solution storage options
    save_solution: Optional[bool] = Field(
        False,
        description="Automatically save the solution to storage. Returns solution_id in response.",
    )
    solution_ttl_days: Optional[int] = Field(
        None,
        ge=1,
        description="Time-to-live in days for saved solution (default: 30). Only used if save_solution=True.",
    )
    solution_tags: Optional[List[str]] = Field(
        None,
        description="Tags to apply to saved solution. Only used if save_solution=True.",
    )

    # Tree filtering parameters (for nested matching results)
    include_trees: Optional[bool] = Field(
        True,
        description="Include full tree data in response. If False, returns metadata only (tree counts, IDs).",
    )
    component_id: Optional[str] = Field(
        None,
        description="Filter trees by component ID (for nested matching).",
    )
    component_name: Optional[str] = Field(
        None,
        description="Filter trees by component name (for nested matching).",
    )
    facility_id: Optional[UUID] = Field(
        None,
        description="Filter trees by facility ID (for nested matching).",
    )
    facility_name: Optional[str] = Field(
        None,
        description="Filter trees by facility name (for nested matching).",
    )
    depth: Optional[int] = Field(
        None,
        ge=0,
        description="Filter trees by exact depth level (for nested matching).",
    )
    min_depth: Optional[int] = Field(
        None,
        ge=0,
        description="Filter trees by minimum depth level (for nested matching).",
    )
    max_depth_filter: Optional[int] = Field(
        None,
        ge=0,
        description="Filter trees by maximum depth level (for nested matching). Note: distinct from max_depth which controls BOM explosion depth.",
    )

    include_workflows: Optional[bool] = False

    # Legacy fields kept for backward compatibility
    optimization_criteria: Optional[Dict[str, float]] = Field(
        default_factory=dict,
        description="Optional weights for different optimization criteria",
    )
    okw_filters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional filters for OKW facilities (e.g., location, capabilities)",
    )
    okw_facilities: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Optional list of OKW facilities (as dicts) to use instead of loading from storage",
    )
    okw_ids: Optional[List[str]] = Field(
        None,
        description=(
            "Restrict matching to this subset of OKW facility IDs. Facilities are still "
            "loaded from the configured source (or okw_facilities), then filtered to these "
            "IDs before matching. An empty or omitted list means match against all facilities."
        ),
    )
    network_filter: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Match against the unified network surface (local OKW ∪ Maps of Making) "
            "narrowed by these filters — same keys as GET /api/okw/spaces "
            "(include_mom, country, city, process, source, status, region, access_type). "
            "When set, it supersedes the storage/okw_ids candidate pool so a design can "
            "be matched against exactly the filtered set the network browse view shows."
        ),
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "okh_manifest": {
                    "title": "Test OKH Manifest",
                    "version": "1.0.0",
                    "manufacturing_specs": {
                        "process_requirements": [
                            {"process_name": "PCB Assembly", "parameters": {}}
                        ]
                    },
                },
                "access_type": "public",
                "facility_status": "active",
                "min_confidence": 0.8,
                "max_results": 5,
                "max_distance_km": 50.0,
                "deadline": "2024-12-31T23:59:59Z",
                "max_cost": 10000.0,
                "min_capacity": 100,
                "location_coords": {"lat": 37.7749, "lng": -122.4194},
                "include_workflows": False,
                "max_depth": 0,  # 0 = single-level, > 0 = nested matching
                "auto_detect_depth": False,
                "include_validation": True,
                "include_human_summary": False,
                "human_summary_profile": "balanced",
                "allow_facility_combinations": False,
                "max_facilities_per_solution": 3,
                "return_alternative_solutions": True,
                "combination_strategy": "greedy",
                "use_llm": True,
                "llm_provider": "anthropic",
                "llm_model": "claude-sonnet-4-5",
                "quality_level": "professional",
                "strict_mode": False,
            }
        }
    )

    @model_validator(mode="after")
    def validate_input(self):
        """Ensure exactly one input type is provided (either manufacturing or cooking domain)"""
        manufacturing_fields = [
            f
            for f, v in [
                ("okh_id", self.okh_id),
                ("okh_manifest", self.okh_manifest),
                ("okh_url", self.okh_url),
            ]
            if v is not None
        ]
        cooking_fields = [
            f
            for f, v in [
                ("recipe_id", self.recipe_id),
                ("recipe", self.recipe),
                ("recipe_url", self.recipe_url),
            ]
            if v is not None
        ]

        if len(manufacturing_fields) > 1:
            raise ValueError(
                f"Cannot provide multiple OKH inputs: {', '.join(manufacturing_fields)}"
            )
        if len(cooking_fields) > 1:
            raise ValueError(
                f"Cannot provide multiple recipe inputs: {', '.join(cooking_fields)}"
            )
        if manufacturing_fields and cooking_fields:
            raise ValueError(
                "Cannot provide both manufacturing (OKH) and cooking (recipe) inputs. Choose one domain."
            )
        if not manufacturing_fields and not cooking_fields:
            raise ValueError(
                "Must provide either okh_id/okh_manifest/okh_url (manufacturing) or recipe_id/recipe/recipe_url (cooking)"
            )

        return self


class ValidateMatchRequest(BaseModel):
    """Request model for validating an existing supply tree"""

    okh_id: UUID
    supply_tree_id: UUID

    validation_criteria: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Optional criteria for validation"
    )


class FacilityMatchRequest(BaseAPIRequest):
    """Reverse-match request: which designs can a given facility produce?"""

    okw_id: UUID = Field(
        ..., description="Facility (OKW) to find producible designs for"
    )
    domain: Optional[str] = Field(
        None,
        description="Optional explicit domain; skips content-based domain detection.",
    )
    min_confidence: Optional[float] = Field(
        0.1,
        ge=0.0,
        le=1.0,
        description="Minimum solution score for a design to be reported.",
    )
    max_results: Optional[int] = Field(
        10, ge=1, description="Maximum number of designs to return."
    )


class SimulationParameters(BaseModel):
    """Parameters for simulation"""

    start_time: str

    resource_availability: Dict[str, Any] = Field(default_factory=dict)


class SimulateRequest(BaseModel):
    """Request model for simulating execution of a supply tree"""

    supply_tree: Dict[str, Any]
    parameters: SimulationParameters
