"""Request models for LLM credential management."""

from typing import Optional

from pydantic import BaseModel, Field


class LLMCredentialUpsert(BaseModel):
    """Set or rotate an LLM provider API key."""

    api_key: str = Field(..., min_length=1, description="Provider API key (plaintext)")
    model: Optional[str] = Field(
        None, description="Optional default model for this provider"
    )
    activate: bool = Field(
        True,
        description="When true, hot-swap into the running LLM service as the active provider",
    )
