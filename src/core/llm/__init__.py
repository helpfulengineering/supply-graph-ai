"""
LLM Provider System for the Open Hardware Manager.

This module provides a LLM provider abstraction system that supports
multiple LLM providers (OpenAI, Anthropic, Google, Azure, Local) with a unified
interface for generation and matching operations.

The LLM system includes:
- Provider abstraction layer with standardized interfaces
- Multiple provider implementations (OpenAI, Anthropic, Google, Local)
- LLM service for provider management and request routing
- Cost tracking and usage analytics
- Response caching and optimization
- Error handling and fallback mechanisms

All LLM operations are handled through the LLM service, which manages provider
selection, request routing, and response processing.
"""

from .models.metrics import LLMMetrics
from .models.requests import (
    LLMPayloadSection,
    LLMRequest,
    LLMRequestConfig,
    LLMRequestType,
    LLMStructuredRequest,
    LLMTraceContext,
)
from .models.responses import LLMResponse, LLMResponseStatus
from .providers.anthropic import AnthropicProvider
from .providers.base import BaseLLMProvider, LLMProviderConfig, LLMProviderType
from .service import LLMService, LLMServiceConfig
from .chunking import (
    ChunkingConfig,
    TextChunk,
    TokenBudget,
    TokenBudgetPolicy,
    build_token_budget,
    default_token_estimator,
    split_text_into_chunks,
)

__all__ = [
    "BaseLLMProvider",
    "LLMProviderConfig",
    "LLMProviderType",
    "AnthropicProvider",
    "LLMRequest",
    "LLMRequestConfig",
    "LLMRequestType",
    "LLMPayloadSection",
    "LLMTraceContext",
    "LLMStructuredRequest",
    "LLMResponse",
    "LLMResponseStatus",
    "LLMMetrics",
    "LLMService",
    "LLMServiceConfig",
    "TextChunk",
    "ChunkingConfig",
    "TokenBudget",
    "TokenBudgetPolicy",
    "build_token_budget",
    "default_token_estimator",
    "split_text_into_chunks",
]
