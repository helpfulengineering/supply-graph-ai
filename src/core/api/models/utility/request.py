from pydantic import BaseModel, ConfigDict
from typing import Optional

from ..base import BaseAPIRequest, LLMRequestMixin


class DomainFilterRequest(BaseAPIRequest, LLMRequestMixin):
    """Request model for filtering domains"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "manufacturing",
                "active_only": True,
                "use_llm": True,
                "llm_provider": "anthropic",
                "llm_model": "claude-sonnet-4-5",
                "quality_level": "professional",
                "strict_mode": False,
            }
        }
    )

    # Optional fields
    name: Optional[str] = None
    active_only: bool = True


class ContextFilterRequest(BaseAPIRequest, LLMRequestMixin):
    """Request model for filtering contexts within a domain"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "professional",
                "include_deprecated": False,
                "with_details": True,
                "use_llm": True,
                "llm_provider": "anthropic",
                "llm_model": "claude-sonnet-4-5",
                "quality_level": "professional",
                "strict_mode": False,
            }
        }
    )

    # Optional fields
    name: Optional[str] = None
    include_deprecated: bool = False
    with_details: bool = False
