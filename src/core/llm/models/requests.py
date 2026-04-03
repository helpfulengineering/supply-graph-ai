"""
LLM Request Models for the Open Hardware Manager.

This module provides data models for LLM requests and configuration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel


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


@dataclass
class LLMPayloadSection:
    """Named section of text for structured long-context workflows."""

    name: str
    text: str
    chunkable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Payload section name cannot be empty")
        if not self.text or not self.text.strip():
            raise ValueError("Payload section text cannot be empty")


@dataclass
class LLMTraceContext:
    """Trace metadata for chunked or multi-step request execution."""

    job_id: Optional[str] = None
    callsite: Optional[str] = None
    prompt_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMStructuredRequest:
    """Structured request model for chunked map-reduce style workflows."""

    instruction: str
    payload_sections: List[LLMPayloadSection]
    request_type: LLMRequestType
    config: LLMRequestConfig
    output_schema: Optional[Dict[str, Any]] = None
    map_output_schema: Optional[Type[BaseModel]] = None
    reduce_output_schema: Optional[Type[BaseModel]] = None
    repair_attempts: int = 1
    trace_context: Optional[LLMTraceContext] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.instruction or not self.instruction.strip():
            raise ValueError("Instruction cannot be empty")
        if not self.payload_sections:
            raise ValueError("payload_sections cannot be empty")
        if self.repair_attempts < 0:
            raise ValueError("repair_attempts must be >= 0")

        if self.config.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

        if not 0.0 <= self.config.temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")

        if not 0.0 <= self.config.top_p <= 1.0:
            raise ValueError("top_p must be between 0.0 and 1.0")
