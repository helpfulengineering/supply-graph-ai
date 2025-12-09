from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ....models.okh import OKHManifest
from ..base import BaseAPIRequest, LLMRequestMixin


class OptimizationCriteria(BaseModel):
    """Model for optimization criteria"""

    # Required fields first
    priority: str  # "cost", "time", "quality"

    # Optional fields after
    weights: Dict[str, float] = Field(default_factory=dict)


class MatchRequest(BaseAPIRequest, LLMRequestMixin):
    """Consolidated match request with standardized fields and LLM support"""

    # Core matching fields - either okh_id, okh_manifest, okh_url, recipe_id, recipe, or recipe_url must be provided
    # Manufacturing domain fields
    okh_id: Optional[UUID] = None
    okh_manifest: Optional[dict] = (
        None  # Changed from OKHManifest to dict for API compatibility
    )
    okh_url: Optional[str] = Field(None, description="URL to fetch OKH manifest from")

    # Cooking domain fields
    recipe_id: Optional[UUID] = None
    recipe: Optional[dict] = None  # Recipe data (for cooking domain)
    recipe_url: Optional[str] = Field(None, description="URL to fetch recipe from")

    # Domain override (optional - will be auto-detected if not provided)
    domain: Optional[str] = Field(
        None,
        description="Domain override (manufacturing, cooking). Auto-detected if not provided",
    )

    # Enhanced filtering options
    access_type: Optional[str] = None
    facility_status: Optional[str] = None
    location: Optional[str] = None
    capabilities: Optional[List[str]] = None
    materials: Optional[List[str]] = None

    # Advanced filtering parameters
    max_distance_km: Optional[float] = None  # Distance filter
    deadline: Optional[str] = None  # Timeline filter (ISO datetime string)
    max_cost: Optional[float] = None  # Budget filter
    min_capacity: Optional[int] = None  # Capacity filter
    location_coords: Optional[Dict[str, float]] = None  # {"lat": 0.0, "lng": 0.0}

    # Quality and validation options
    min_confidence: Optional[float] = 0.3  # Relaxed default to show more matches
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

    # Backward compatibility
    include_workflows: Optional[bool] = False  # Feature flag for workflow inclusion

    # Legacy fields for backward compatibility
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
        manufacturing_fields = []
        cooking_fields = []

        if self.okh_id is not None:
            manufacturing_fields.append("okh_id")
        if self.okh_manifest is not None:
            manufacturing_fields.append("okh_manifest")
        if self.okh_url is not None:
            manufacturing_fields.append("okh_url")

        if self.recipe_id is not None:
            cooking_fields.append("recipe_id")
        if self.recipe is not None:
            cooking_fields.append("recipe")
        if self.recipe_url is not None:
            cooking_fields.append("recipe_url")

        # Check for multiple inputs within same domain
        if len(manufacturing_fields) > 1:
            raise ValueError(
                f"Cannot provide multiple OKH inputs: {', '.join(manufacturing_fields)}"
            )
        if len(cooking_fields) > 1:
            raise ValueError(
                f"Cannot provide multiple recipe inputs: {', '.join(cooking_fields)}"
            )

        # Check for cross-domain inputs
        if len(manufacturing_fields) > 0 and len(cooking_fields) > 0:
            raise ValueError(
                f"Cannot provide both manufacturing (OKH) and cooking (recipe) inputs. Choose one domain."
            )

        # Must provide at least one input
        if len(manufacturing_fields) == 0 and len(cooking_fields) == 0:
            raise ValueError(
                "Must provide either okh_id/okh_manifest/okh_url (manufacturing) or recipe_id/recipe/recipe_url (cooking)"
            )

        return self


class ValidateMatchRequest(BaseModel):
    """Request model for validating an existing supply tree"""

    # Required fields first
    okh_id: UUID
    supply_tree_id: UUID

    # Optional fields after
    validation_criteria: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Optional criteria for validation"
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
