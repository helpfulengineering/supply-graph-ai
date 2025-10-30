"""
LLM Provider System for the Open Matching Engine.

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

from .providers.base import BaseLLMProvider, LLMProviderConfig, LLMProviderType
from .providers.anthropic import AnthropicProvider
from .models.requests import LLMRequest, LLMRequestConfig, LLMRequestType
from .models.responses import LLMResponse, LLMResponseStatus
from .models.metrics import LLMMetrics
from .service import LLMService, LLMServiceConfig

__all__ = [
    "BaseLLMProvider",
    "LLMProviderConfig",
    "LLMProviderType",
    "AnthropicProvider",
    "LLMRequest",
    "LLMRequestConfig",
    "LLMRequestType",
    "LLMResponse",
    "LLMResponseStatus",
    "LLMMetrics",
    "LLMService",
    "LLMServiceConfig",
]
