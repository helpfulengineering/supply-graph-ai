from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from ..base import LLMResponseMixin, SuccessResponse
from ..base import ValidationResult as BaseValidationResult


class Domain(BaseModel):
    """Model for domain information"""

    id: str
    name: str
    description: str


class DomainsResponse(SuccessResponse, LLMResponseMixin):
    """Response model for available domains with standardized fields and LLM information

    .. warning::
       Not what GET /api/utility/domains returns, and not used by it. This
       declares ``domains``/``default_domain`` at the TOP level; the route
       nests them under ``data``. Attaching this as a ``response_model`` would
       filter the real payload away. ``DomainListResponse`` below is the one
       that matches the route.
    """

    domains: List[Domain]
    # Which domain a fresh browser session should open in on this instance
    # (OHM_DEFAULT_DOMAIN setting; "manufacturing" unless a deployment opts
    # into e.g. a dedicated cooking-domain instance).
    default_domain: str = "manufacturing"

    processing_time: float = 0.0
    validation_results: Optional[List[BaseValidationResult]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "domains": [
                    {
                        "id": "manufacturing",
                        "name": "Manufacturing Domain",
                        "description": "Hardware manufacturing capabilities",
                    }
                ],
                "default_domain": "manufacturing",
                "status": "success",
                "message": "Domains retrieved successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "processing_time": 0.1,
                "llm_used": True,
                "llm_provider": "anthropic",
                "llm_cost": 0.001,
                "data": {},
                "validation_results": [],
            }
        }
    )


class Context(BaseModel):
    """Model for validation context information"""

    id: str
    name: str
    description: str


class ContextsResponse(SuccessResponse, LLMResponseMixin):
    """Response model for validation contexts with standardized fields and LLM information"""

    contexts: List[Context]

    processing_time: float = 0.0
    validation_results: Optional[List[BaseValidationResult]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "contexts": [
                    {
                        "id": "professional",
                        "name": "Professional Manufacturing",
                        "description": "Commercial-grade production",
                    }
                ],
                "status": "success",
                "message": "Contexts retrieved successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "processing_time": 0.1,
                "llm_used": True,
                "llm_provider": "anthropic",
                "llm_cost": 0.001,
                "data": {},
                "validation_results": [],
            }
        }
    )


class ErrorResponse(BaseModel):
    """Response model for API errors"""

    error: Dict[str, Any]  # Contains code, message, details


class DomainListData(BaseModel):
    """The ``data`` payload of GET /api/utility/domains.

    Derived from the payload captured in ``tests/api/golden/utility_domains.json``
    before this model existed. Note the nesting: the route puts these under
    ``data``, which is why ``DomainsResponse`` above — which declares them at
    the top level — does not describe this route and is not used by it.
    """

    default_domain: str
    domains: List[Domain]
    #: Per-domain validation reports. Left free-form: they come from the domain
    #: validators, and a strict model would filter whatever those grow next.
    validation_results: List[Dict[str, Any]]
    processing_time: float


class DomainListResponse(SuccessResponse):
    data: DomainListData
