from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ..base import LLMResponseMixin, SuccessResponse
from ..base import ValidationResult as BaseValidationResult


class ValidationIssue(BaseModel):
    """Model for validation issues"""

    severity: str  # "error", "warning", "info"
    message: str

    path: List[str] = []


class Capability(BaseModel):
    """Model for extracted capabilities"""

    type: str

    parameters: Dict[str, Any] = {}
    limitations: Dict[str, Any] = {}


class OKWResponse(SuccessResponse, LLMResponseMixin):
    """Response model for OKW facilities with standardized fields and LLM information"""

    message: str = "OKW facility operation completed successfully"
    id: UUID
    name: str
    location: Dict[str, Any]
    facility_status: str
    access_type: str

    owner: Optional[Dict[str, Any]] = None
    contact: Optional[Dict[str, Any]] = None
    affiliations: List[Dict[str, Any]] = []
    opening_hours: Optional[str] = None
    description: Optional[str] = None
    date_founded: Optional[str] = None
    wheelchair_accessibility: Optional[str] = None
    equipment: List[Dict[str, Any]] = []
    manufacturing_processes: List[str] = []
    typical_batch_size: Optional[str] = None
    floor_size: Optional[int] = None
    storage_capacity: Optional[str] = None
    typical_materials: List[Dict[str, Any]] = []
    #: How far this facility may travel from the node. Carried on search results
    #: so the UI can surface a facility its owner created but has not shared —
    #: a caller only ever sees shareable records plus their own.
    visibility: Optional[str] = None
    certifications: List[str] = []
    metadata: Dict[str, Any] = {}
    domain: Optional[str] = None  # "manufacturing" or "cooking"

    processing_time: float = 0.0
    validation_results: Optional[List[BaseValidationResult]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "OKW operation completed successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "facility": {
                    "id": "facility_123",
                    "name": "TechFab Manufacturing Hub",
                    "facility_status": "active",
                },
                "processing_time": 1.25,
                "llm_used": True,
                "llm_provider": "anthropic",
                "llm_cost": 0.012,
                "data": {},
                "metadata": {},
            }
        }
    )


class OKWValidationResponse(BaseModel):
    """Response model for OKW validation"""

    valid: bool
    normalized_content: Dict[str, Any]

    issues: Optional[List[ValidationIssue]] = None


class OKWExtractResponse(BaseModel):
    """Response model for capability extraction"""

    capabilities: List[Capability]


class OKWListResponse(BaseModel):
    """Response model for listing OKW facilities"""

    results: List[OKWResponse]
    total: int
    page: int
    page_size: int


class OKWUploadResponse(BaseModel):
    """Response model for OKW file upload"""

    success: bool
    message: str
    okw: OKWResponse

    validation_issues: Optional[List[ValidationIssue]] = None


class OKWExportResponse(BaseModel):
    """Response model for OKW schema export"""

    success: bool
    message: str
    json_schema: Dict[
        str, Any
    ]  # Renamed from 'schema' to avoid shadowing BaseModel.schema

    schema_version: Optional[str] = "http://json-schema.org/draft-07/schema#"
    model_name: Optional[str] = "ManufacturingFacility"


class NetworkSpace(BaseModel):
    """One space on the unified network surface — a local OKW facility or a
    Maps of Making entry, projected to a common shape and source-labelled.

    Every optional field here is required-but-nullable: the projection always
    emits the key and may set it to null (a facility with no coordinates, an
    owner with no website). Giving these defaults would mark them optional in
    the schema, and clients would then handle an `undefined` the route never
    sends.

    Derived from the payload captured in
    ``tests/api/golden/okw_spaces_shape.json`` before this model existed.
    """

    id: str
    name: str
    lat: Optional[float]
    lon: Optional[float]
    city: Optional[str]
    region: Optional[str]
    country: Optional[str]
    #: "local" (an OKW facility on this node) or "mom" (Maps of Making). The
    #: projection sets these literally, and the UI keys colour and labels off
    #: them, so the union is part of the contract rather than an implementation
    #: detail.
    source: Literal["local", "mom"]
    status: Optional[str]
    processes: List[str]
    access_type: Optional[str]
    url: Optional[str]
    #: Set when the country could not be resolved unambiguously; these sort last.
    ambiguous: bool


class NetworkSpacesResponse(BaseModel):
    """GET /api/okw/spaces. Not the SuccessResponse envelope — this route
    returns its payload at the top level."""

    success: bool
    spaces: List[NetworkSpace]
    total: int
    local_count: int
    mom_count: int
    dropped_no_coords: int
    #: False when the Maps of Making fetch failed or was not requested; the
    #: surface degrades to local-only rather than erroring.
    mom_available: bool


class OKWTemplateResponse(BaseModel):
    """GET /api/okw/template — a blank facility for a client to fill in."""

    success: bool
    #: The blank facility itself. Free-form on purpose: it mirrors the OKW
    #: model, and a strict copy here would filter whatever that model grows.
    template: Dict[str, Any]
    model_name: str
