"""
Response models for LLM API endpoints.

This module provides Pydantic models for LLM API responses.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..base import SuccessResponse


class ProviderStatus(BaseModel):
    """Status information for an LLM provider."""

    name: str = Field(..., description="Provider name")
    type: str = Field(..., description="Provider type")
    status: str = Field(
        ..., description="Provider status (healthy, unhealthy, not_available, error)"
    )
    model: Optional[str] = Field(None, description="Current model")
    is_connected: Optional[bool] = Field(
        None, description="Whether provider is connected"
    )
    available_models: Optional[List[str]] = Field(
        None, description="List of available models"
    )
    error: Optional[str] = Field(None, description="Error message if status is error")


class LLMHealthResponse(SuccessResponse):
    """Response model for LLM health check."""

    health_status: str = Field(
        ..., description="Overall LLM service status (healthy, degraded, unavailable)"
    )
    providers: Dict[str, ProviderStatus] = Field(
        ..., description="Provider status information"
    )
    metrics: Dict[str, Any] = Field(..., description="LLM service metrics")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "LLM service health check completed",
                "timestamp": "2024-01-01T12:00:00Z",
                "health_status": "healthy",
                "providers": {
                    "anthropic": {
                        "name": "anthropic",
                        "type": "anthropic",
                        "status": "healthy",
                        "model": "claude-sonnet-4-5-20250929",
                        "is_connected": True,
                        "available_models": ["claude-sonnet-4-5-20250929"],
                    }
                },
                "metrics": {
                    "total_requests": 150,
                    "total_cost": 0.45,
                    "average_cost_per_request": 0.003,
                    "active_provider": "anthropic",
                    "available_providers": ["anthropic"],
                },
            }
        }
    )


class LLMProvidersResponse(SuccessResponse):
    """Response model for LLM providers list."""

    providers: List[ProviderStatus] = Field(
        ..., description="List of available providers"
    )
    default_provider: Optional[str] = Field(None, description="Default provider name")
    available_providers: List[str] = Field(
        ..., description="List of available provider names"
    )


class LLMCredentialStatus(BaseModel):
    """Public view of a stored LLM credential — never includes the full key."""

    provider: str = Field(..., description="Provider name")
    model: Optional[str] = Field(None, description="Configured default model")
    masked_key: str = Field(..., description="Masked API key suffix")
    configured: bool = Field(True, description="Whether a credential is stored")
    is_active: bool = Field(
        False,
        description=(
            "Whether this is the provider the node uses. Recorded durably, so "
            "it survives a restart and is the same answer in every worker."
        ),
    )


class LLMCredentialListResponse(SuccessResponse):
    """List of stored LLM credentials (masked)."""

    credentials: List[LLMCredentialStatus] = Field(
        default_factory=list, description="Configured provider credentials"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Providers retrieved successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "providers": [
                    {
                        "name": "anthropic",
                        "type": "anthropic",
                        "status": "healthy",
                        "model": "claude-sonnet-4-5-20250929",
                        "is_connected": True,
                        "available_models": ["claude-sonnet-4-5-20250929"],
                    }
                ],
                "default_provider": "anthropic",
                "available_providers": ["anthropic"],
            }
        }
    )
