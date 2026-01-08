"""
OpenAI LLM Provider for the Open Hardware Manager.

This module provides an implementation of the BaseLLMProvider interface
for OpenAI's models, including GPT-3.5, GPT-4, GPT-4-turbo, and other variants.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import openai
from openai import AsyncOpenAI

from ..models.requests import LLMRequest, LLMRequestConfig
from ..models.responses import LLMResponse, LLMResponseMetadata, LLMResponseStatus
from .base import BaseLLMProvider, LLMProviderConfig, LLMProviderType

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI LLM provider implementation for GPT models.

    This provider supports all OpenAI models including:
    - GPT-3.5-turbo
    - GPT-4
    - GPT-4-turbo
    - GPT-4o
    - GPT-4o-mini
    """

    # OpenAI model pricing (per 1M tokens, as of 2024)
    MODEL_PRICING = {
        "gpt-4o": {"input": 5.0, "output": 15.0},  # $5/$15 per 1M tokens
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},  # $0.15/$0.6 per 1M tokens
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},  # $10/$30 per 1M tokens
        "gpt-4": {"input": 30.0, "output": 60.0},  # $30/$60 per 1M tokens
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},  # $0.5/$1.5 per 1M tokens
        "gpt-3.5-turbo-16k": {"input": 3.0, "output": 4.0},  # $3/$4 per 1M tokens
    }

    # Available models
    AVAILABLE_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
    ]

    def __init__(self, config: LLMProviderConfig):
        """
        Initialize the OpenAI provider.

        Args:
            config: Configuration for the provider

        Raises:
            ValueError: If configuration is invalid
        """
        super().__init__(config)
        self._client: Optional[AsyncOpenAI] = None

        # Validate that this is an OpenAI provider
        if config.provider_type != LLMProviderType.OPENAI:
            raise ValueError(
                f"Provider type must be OPENAI, got {config.provider_type}"
            )

    async def connect(self) -> None:
        """
        Connect to the OpenAI API.

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If API key is invalid
        """
        try:
            # Only pass parameters that AsyncOpenAI actually accepts
            client_kwargs = {
                "api_key": self.config.api_key,
            }

            # Add optional parameters only if they're provided
            if self.config.base_url:
                client_kwargs["base_url"] = self.config.base_url

            self._client = AsyncOpenAI(**client_kwargs)

            # Skip connection test to avoid hanging during initialization
            # The connection will be tested on the first actual request
            self._connected = True
            self._logger.info(f"Connected to OpenAI API with model {self.config.model}")

        except Exception as e:
            self._connected = False
            self._logger.error(f"Failed to connect to OpenAI API: {e}")
            raise ConnectionError(f"Failed to connect to OpenAI API: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the OpenAI API."""
        if self._client:
            # OpenAI client doesn't have explicit disconnect, just clear the reference
            self._client = None

        self._connected = False
        self._logger.info("Disconnected from OpenAI API")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response using OpenAI's GPT model.

        Args:
            request: The LLM request to process

        Returns:
            LLMResponse: The generated response

        Raises:
            LLMError: If the request fails
            RateLimitError: If rate limit is exceeded
            TimeoutError: If the request times out
        """
        if not self._connected or not self._client:
            raise ConnectionError("Provider not connected")

        start_time = datetime.now()

        try:
            # Prepare the request for OpenAI
            openai_request = self._prepare_openai_request(request)

            # Make the API call
            response = await self._client.chat.completions.create(**openai_request)

            # Process the response
            llm_response = self._process_openai_response(response, request, start_time)

            # Update metrics
            self._update_metrics(llm_response, start_time)

            return llm_response

        except openai.RateLimitError as e:
            self._logger.warning(f"Rate limit exceeded: {e}")
            raise RateLimitError(f"Rate limit exceeded: {e}")

        except openai.APITimeoutError as e:
            self._logger.warning(f"Request timeout: {e}")
            raise TimeoutError(f"Request timeout: {e}")

        except openai.APIError as e:
            self._logger.error(f"OpenAI API error: {e}")
            raise LLMError(f"OpenAI API error: {e}")

        except Exception as e:
            self._logger.error(f"Unexpected error: {e}")
            raise LLMError(f"Unexpected error: {e}")

    async def health_check(self) -> bool:
        """
        Check if the OpenAI provider is healthy.

        Returns:
            bool: True if healthy, False otherwise
        """
        if not self._connected or not self._client:
            return False

        try:
            # Make a simple test request
            await self._test_connection()
            return True

        except Exception as e:
            self._logger.warning(f"Health check failed: {e}")
            return False

    def get_available_models(self) -> List[str]:
        """
        Get list of available OpenAI models.

        Returns:
            List[str]: List of available model names
        """
        return self.AVAILABLE_MODELS.copy()

    def estimate_cost(self, request: LLMRequest) -> float:
        """
        Estimate the cost of a request.

        Args:
            request: The request to estimate cost for

        Returns:
            float: Estimated cost in USD
        """
        if self.config.model not in self.MODEL_PRICING:
            # Default pricing if model not found
            return 0.0

        pricing = self.MODEL_PRICING[self.config.model]

        # Rough estimation based on prompt length
        # This is a simplified estimation - actual tokenization would be more accurate
        estimated_input_tokens = (
            len(request.prompt.split()) * 1.3
        )  # Rough token estimation
        estimated_output_tokens = (
            request.config.max_tokens * 0.5
        )  # Assume 50% of max tokens used

        input_cost = (estimated_input_tokens / 1_000_000) * pricing["input"]
        output_cost = (estimated_output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def _prepare_openai_request(self, request: LLMRequest) -> Dict[str, Any]:
        """Prepare the request for OpenAI API."""
        return {
            "model": self.config.model,
            "max_tokens": request.config.max_tokens,
            "temperature": request.config.temperature,
            "messages": [{"role": "user", "content": request.prompt}],
        }

    def _process_openai_response(
        self, response: Any, request: LLMRequest, start_time: datetime
    ) -> LLMResponse:
        """Process the OpenAI API response."""
        processing_time = (datetime.now() - start_time).total_seconds()

        # Extract content from response
        content = ""
        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content or ""

        # Calculate tokens used
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0
        total_tokens = input_tokens + output_tokens

        # Calculate cost
        cost = self._calculate_cost(input_tokens, output_tokens)

        # Create metadata
        metadata = LLMResponseMetadata(
            provider="openai",
            model=self.config.model,
            tokens_used=total_tokens,
            cost=cost,
            processing_time=processing_time,
            request_id=request.request_id,
            response_id=response.id if hasattr(response, "id") else None,
            metadata={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "finish_reason": (
                    response.choices[0].finish_reason if response.choices else None
                ),
            },
        )

        return LLMResponse(
            content=content,
            status=LLMResponseStatus.SUCCESS,
            metadata=metadata,
            raw_response={
                "id": response.id if hasattr(response, "id") else None,
                "model": response.model if hasattr(response, "model") else None,
                "usage": (
                    {
                        "prompt_tokens": input_tokens,
                        "completion_tokens": output_tokens,
                        "total_tokens": total_tokens,
                    }
                    if response.usage
                    else None
                ),
                "finish_reason": (
                    response.choices[0].finish_reason if response.choices else None
                ),
            },
        )

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate the cost based on token usage."""
        if self.config.model not in self.MODEL_PRICING:
            return 0.0

        pricing = self.MODEL_PRICING[self.config.model]

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    async def _test_connection(self) -> None:
        """Test the connection with a simple request."""
        if not self._client:
            raise ConnectionError("Client not initialized")

        # Make a minimal test request
        test_response = await self._client.chat.completions.create(
            model=self.config.model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Hello"}],
        )

        if not test_response:
            raise ConnectionError("Test request failed")

    def _update_metrics(self, response: LLMResponse, start_time: datetime) -> None:
        """Update provider metrics."""
        processing_time = (datetime.now() - start_time).total_seconds()

        self.metrics.add_request(
            success=response.is_success,
            tokens=response.tokens_used,
            cost=response.cost,
            response_time=processing_time,
            provider="openai",
            model=self.config.model,
            error_type=None if response.is_success else "api_error",
        )


# Custom exceptions for better error handling
class LLMError(Exception):
    """Base exception for LLM-related errors."""

    pass


class RateLimitError(LLMError):
    """Exception raised when rate limit is exceeded."""

    pass


class TimeoutError(LLMError):
    """Exception raised when request times out."""

    pass


class ConnectionError(LLMError):
    """Exception raised when connection fails."""

    pass
