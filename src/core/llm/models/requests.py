"""
LLM Request Models for the Open Matching Engine.

This module provides data models for LLM requests and configuration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class LLMRequestType(Enum):
    """Types of LLM requests."""

    GENERATION = "generation"
    MATCHING = "matching"
    VALIDATION = "validation"
    ANALYSIS = "analysis"


@dataclass
class LLMRequestConfig:
    """Configuration for LLM requests."""

    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMRequest:
    """Base LLM request model."""

    prompt: str
    request_type: LLMRequestType
    config: LLMRequestConfig
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate request after initialization."""
        if not self.prompt or not self.prompt.strip():
            raise ValueError("Prompt cannot be empty")

        if self.config.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

        if not 0.0 <= self.config.temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")

        if not 0.0 <= self.config.top_p <= 1.0:
            raise ValueError("top_p must be between 0.0 and 1.0")
