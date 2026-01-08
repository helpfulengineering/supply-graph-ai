"""
Azure OpenAI LLM Provider for the Open Hardware Manager.

This module provides an implementation of the BaseLLMProvider interface
for Azure OpenAI Service, which provides access to OpenAI models (GPT-3.5, GPT-4, etc.)
through Azure's infrastructure.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from ..models.requests import LLMRequest, LLMRequestConfig
from ..models.responses import LLMResponse, LLMResponseMetadata, LLMResponseStatus
from .base import BaseLLMProvider, LLMProviderConfig, LLMProviderType

logger = logging.getLogger(__name__)


@dataclass
class AzureOpenAIProviderConfig(LLMProviderConfig):
    """Configuration for Azure OpenAI provider."""

    deployment_id: str = ""  # Azure deployment name
    api_version: str = "2024-05-01-preview"  # API version
    resource_name: Optional[str] = None  # Auto-extracted from base_url if not provided

    def __post_init__(self):
        """Validate Azure OpenAI specific configuration."""
        super().__post_init__()
        if not self.deployment_id:
            raise ValueError("deployment_id is required for Azure OpenAI provider")
        if not self.api_key:
            raise ValueError("api_key is required for Azure OpenAI provider")
        if not self.base_url:
            raise ValueError("base_url is required for Azure OpenAI provider")


class AzureOpenAIProvider(BaseLLMProvider):
    """
    Azure OpenAI LLM provider implementation for GPT models hosted on Azure.

    This provider supports all Azure OpenAI deployments including:
    - GPT-4
    - GPT-4-turbo
    - GPT-4o
    - GPT-3.5-turbo
    """

    # Azure OpenAI model pricing (per 1M tokens, same as OpenAI)
    MODEL_PRICING = {
        "gpt-4o": {"input": 5.0, "output": 15.0},  # $5/$15 per 1M tokens
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},  # $0.15/$0.6 per 1M tokens
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},  # $10/$30 per 1M tokens
        "gpt-4": {"input": 30.0, "output": 60.0},  # $30/$60 per 1M tokens
        "gpt-35-turbo": {"input": 0.5, "output": 1.5},  # $0.5/$1.5 per 1M tokens
        "gpt-35-turbo-16k": {"input": 3.0, "output": 4.0},  # $3/$4 per 1M tokens
    }

    # Available models (these depend on what's deployed in Azure)
    AVAILABLE_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-35-turbo",
        "gpt-35-turbo-16k",
    ]

    def __init__(self, config: LLMProviderConfig):
        """
        Initialize the Azure OpenAI provider.

        Args:
            config: Configuration for the provider (should be AzureOpenAIProviderConfig)

        Raises:
            ValueError: If configuration is invalid
        """
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
        self._azure_config: Optional[AzureOpenAIProviderConfig] = None

        # Validate that this is an Azure OpenAI provider
        if config.provider_type != LLMProviderType.AZURE_OPENAI:
            raise ValueError(
                f"Provider type must be AZURE_OPENAI, got {config.provider_type}"
            )

        # Convert to Azure-specific config if needed
        if isinstance(config, AzureOpenAIProviderConfig):
            self._azure_config = config
        else:
            # Try to extract Azure-specific fields from metadata
            metadata = config.metadata or {}
            self._azure_config = AzureOpenAIProviderConfig(
                provider_type=config.provider_type,
                api_key=config.api_key,
                base_url=config.base_url,
                model=config.model,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                timeout=config.timeout,
                retry_attempts=config.retry_attempts,
                retry_delay=config.retry_delay,
                deployment_id=metadata.get("deployment_id", ""),
                api_version=metadata.get("api_version", "2024-05-01-preview"),
                resource_name=metadata.get("resource_name"),
            )

    async def connect(self) -> None:
        """
        Connect to the Azure OpenAI API.

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If API key is invalid
        """
        try:
            # Build the endpoint URL
            endpoint_url = self._build_endpoint_url()

            # Create HTTP client
            self._client = httpx.AsyncClient(
                base_url=endpoint_url,
                timeout=self.config.timeout,
                headers={
                    "Content-Type": "application/json",
                    "api-key": self.config.api_key,  # Azure uses api-key header, not Authorization
                },
            )

            # Skip connection test to avoid hanging during initialization
            # The connection will be tested on the first actual request
            self._connected = True
            self._logger.info(
                f"Connected to Azure OpenAI API with deployment {self._azure_config.deployment_id}"
            )

        except Exception as e:
            self._connected = False
            self._logger.error(f"Failed to connect to Azure OpenAI API: {e}")
            raise ConnectionError(f"Failed to connect to Azure OpenAI API: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the Azure OpenAI API."""
        if self._client:
            await self._client.aclose()
            self._client = None

        self._connected = False
        self._logger.info("Disconnected from Azure OpenAI API")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response using Azure OpenAI's GPT model.

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
            # Prepare the request for Azure OpenAI
            azure_request = self._prepare_azure_request(request)

            # Build the full URL with API version
            url = f"/chat/completions?api-version={self._azure_config.api_version}"

            # Make the API call
            response = await self._client.post(url, json=azure_request)
            response.raise_for_status()
            response_data = response.json()

            # Process the response
            llm_response = self._process_azure_response(
                response_data, request, start_time
            )

            # Update metrics
            self._update_metrics(llm_response, start_time)

            return llm_response

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                self._logger.warning(f"Rate limit exceeded: {e}")
                raise RateLimitError(f"Rate limit exceeded: {e}")
            elif e.response.status_code == 401:
                self._logger.error(f"Authentication failed: {e}")
                raise AuthenticationError(f"Authentication failed: {e}")
            else:
                self._logger.error(f"Azure OpenAI API error: {e}")
                raise LLMError(f"Azure OpenAI API error: {e}")

        except httpx.TimeoutException as e:
            self._logger.warning(f"Request timeout: {e}")
            raise TimeoutError(f"Request timeout: {e}")

        except Exception as e:
            self._logger.error(f"Unexpected error: {e}")
            raise LLMError(f"Unexpected error: {e}")

    async def health_check(self) -> bool:
        """
        Check if the Azure OpenAI provider is healthy.

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
        Get list of available Azure OpenAI models.

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

    def _build_endpoint_url(self) -> str:
        """Build the Azure OpenAI endpoint URL."""
        base_url = self.config.base_url.rstrip("/")
        deployment_id = self._azure_config.deployment_id

        # Azure OpenAI endpoint format:
        # https://{resource-name}.openai.azure.com/openai/deployments/{deployment-id}
        if not base_url.endswith(f"/deployments/{deployment_id}"):
            if not base_url.endswith("/openai/deployments"):
                if not base_url.endswith("/openai"):
                    base_url = f"{base_url}/openai"
                base_url = f"{base_url}/deployments"
            base_url = f"{base_url}/{deployment_id}"

        return base_url

    def _prepare_azure_request(self, request: LLMRequest) -> Dict[str, Any]:
        """Prepare the request for Azure OpenAI API."""
        return {
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.config.temperature,
            "max_tokens": request.config.max_tokens,
            "top_p": request.config.top_p,
            "frequency_penalty": request.config.frequency_penalty,
            "presence_penalty": request.config.presence_penalty,
        }

    def _process_azure_response(
        self, response_data: Dict[str, Any], request: LLMRequest, start_time: datetime
    ) -> LLMResponse:
        """Process the Azure OpenAI API response."""
        processing_time = (datetime.now() - start_time).total_seconds()

        # Extract content from response
        content = ""
        if response_data.get("choices") and len(response_data["choices"]) > 0:
            content = response_data["choices"][0].get("message", {}).get("content", "")

        # Calculate tokens used
        usage = response_data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

        # Calculate cost
        cost = self._calculate_cost(input_tokens, output_tokens)

        # Create metadata
        metadata = LLMResponseMetadata(
            provider="azure_openai",
            model=self.config.model,
            tokens_used=total_tokens,
            cost=cost,
            processing_time=processing_time,
            request_id=request.request_id,
            response_id=response_data.get("id"),
            metadata={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "finish_reason": (
                    response_data["choices"][0].get("finish_reason")
                    if response_data.get("choices")
                    else None
                ),
                "deployment_id": self._azure_config.deployment_id,
            },
        )

        return LLMResponse(
            content=content,
            status=LLMResponseStatus.SUCCESS,
            metadata=metadata,
            raw_response=response_data,
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
        test_request = {
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10,
        }

        url = f"/chat/completions?api-version={self._azure_config.api_version}"
        response = await self._client.post(url, json=test_request)
        response.raise_for_status()

        if not response.json():
            raise ConnectionError("Test request failed")

    def _update_metrics(self, response: LLMResponse, start_time: datetime) -> None:
        """Update provider metrics."""
        processing_time = (datetime.now() - start_time).total_seconds()

        self.metrics.add_request(
            success=response.is_success,
            tokens=response.tokens_used,
            cost=response.cost,
            response_time=processing_time,
            provider="azure_openai",
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


class AuthenticationError(LLMError):
    """Exception raised when authentication fails."""

    pass
