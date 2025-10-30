"""
LLM Response Models for the Open Matching Engine.

This module provides data models for LLM responses and metadata.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class LLMResponseStatus(Enum):
    """Status of LLM responses."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    INVALID_REQUEST = "invalid_request"


@dataclass
class LLMResponseMetadata:
    """Metadata for LLM responses."""
    provider: str
    model: str
    tokens_used: int
    cost: float
    processing_time: float
    request_id: Optional[str] = None
    response_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Base LLM response model."""
    content: str
    status: LLMResponseStatus
    metadata: LLMResponseMetadata
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate response after initialization."""
        if self.status == LLMResponseStatus.SUCCESS and not self.content:
            raise ValueError("Content cannot be empty for successful responses")
        
        if self.status != LLMResponseStatus.SUCCESS and not self.error_message:
            raise ValueError("Error message required for non-success responses")
    
    @property
    def is_success(self) -> bool:
        """Check if the response is successful."""
        return self.status == LLMResponseStatus.SUCCESS
    
    @property
    def tokens_used(self) -> int:
        """Get the number of tokens used."""
        return self.metadata.tokens_used
    
    @property
    def cost(self) -> float:
        """Get the cost of the request."""
        return self.metadata.cost
