"""
Ollama LLM Provider for the Open Matching Engine.

This module provides an implementation of the BaseLLMProvider interface
for local models via Ollama, supporting various open-source models like
Llama, Mistral, CodeLlama, and other locally hosted models.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx

from .base import BaseLLMProvider, LLMProviderConfig, LLMProviderType
from ..models.requests import LLMRequest, LLMRequestConfig
from ..models.responses import LLMResponse, LLMResponseStatus, LLMResponseMetadata

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """
    Ollama LLM provider implementation for local models.

    This provider supports various open-source models including:
    - Llama 2/3 (7B, 13B, 70B)
    - Mistral (7B, 8x7B)
    - CodeLlama (7B, 13B, 34B)
    - Phi-3
    - Gemma
    - And many other Ollama-compatible models
    """

    # Ollama model pricing (free for local models, but we track "cost" as compute time)
    MODEL_PRICING = {
        "llama3": {"input": 0.0, "output": 0.0},  # Free local model
        "llama3:8b": {"input": 0.0, "output": 0.0},  # Free local model
        "llama3:70b": {"input": 0.0, "output": 0.0},  # Free local model
        "mistral": {"input": 0.0, "output": 0.0},  # Free local model
        "mistral:7b": {"input": 0.0, "output": 0.0},  # Free local model
        "codellama": {"input": 0.0, "output": 0.0},  # Free local model
        "codellama:7b": {"input": 0.0, "output": 0.0},  # Free local model
        "phi3": {"input": 0.0, "output": 0.0},  # Free local model
        "gemma": {"input": 0.0, "output": 0.0},  # Free local model
    }

    # Common Ollama models (this will be populated dynamically)
    AVAILABLE_MODELS = [
        "llama3.1:8b",
        "llama3.1:70b",
        "mistral:latest",
        "codellama:latest",
        "deepseek-coder:latest",
        "qwen2.5-coder:1.5b",
        "deepseek-r1:7b",
        "llama2:latest",
    ]

    def __init__(self, config: LLMProviderConfig):
        """
        Initialize the Ollama provider.

        Args:
            config: Configuration for the provider

        Raises:
            ValueError: If configuration is invalid
        """
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
        # Get base URL from config, environment variable, or default
        import os

        default_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._base_url = config.base_url or default_url

        # Validate that this is a LOCAL provider
        if config.provider_type != LLMProviderType.LOCAL:
            raise ValueError(f"Provider type must be LOCAL, got {config.provider_type}")

    async def connect(self) -> None:
        """
        Connect to the Ollama API.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            # Create HTTP client for Ollama API
            self._client = httpx.AsyncClient(
                base_url=self._base_url, timeout=self.config.timeout
            )

            # Test connection by checking if Ollama is running
            await self._test_connection()

            self._connected = True
            self._logger.info(
                f"Connected to Ollama API at {self._base_url} with model {self.config.model}"
            )

        except Exception as e:
            self._connected = False
            self._logger.error(f"Failed to connect to Ollama API: {e}")
            raise ConnectionError(f"Failed to connect to Ollama API: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the Ollama API."""
        if self._client:
            await self._client.aclose()
            self._client = None

        self._connected = False
        self._logger.info("Disconnected from Ollama API")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response using Ollama's local model.

        Args:
            request: The LLM request to process

        Returns:
            LLMResponse: The generated response

        Raises:
            LLMError: If the request fails
            TimeoutError: If the request times out
        """
        if not self._connected or not self._client:
            raise ConnectionError("Provider not connected")

        start_time = datetime.now()

        try:
            # Prepare the request for Ollama
            ollama_request = self._prepare_ollama_request(request)

            # Make the API call
            response = await self._client.post("/api/generate", json=ollama_request)
            response.raise_for_status()

            # Process the streaming response
            llm_response = await self._process_ollama_response(
                response, request, start_time
            )

            # Update metrics
            self._update_metrics(llm_response, start_time)

            return llm_response

        except httpx.TimeoutException as e:
            self._logger.warning(f"Request timeout: {e}")
            raise TimeoutError(f"Request timeout: {e}")

        except httpx.HTTPStatusError as e:
            self._logger.error(f"Ollama API error: {e}")
            raise LLMError(f"Ollama API error: {e}")

        except Exception as e:
            self._logger.error(f"Unexpected error: {e}")
            raise LLMError(f"Unexpected error: {e}")

    async def health_check(self) -> bool:
        """
        Check if the Ollama provider is healthy.

        Returns:
            bool: True if healthy, False otherwise
        """
        if not self._connected or not self._client:
            return False

        try:
            # Check if Ollama is running
            await self._test_connection()
            return True

        except Exception as e:
            self._logger.warning(f"Health check failed: {e}")
            return False

    def get_available_models(self) -> List[str]:
        """
        Get list of available Ollama models.

        Returns:
            List[str]: List of available model names
        """
        return self.AVAILABLE_MODELS.copy()

    async def get_installed_models(self) -> List[str]:
        """
        Get list of models installed in Ollama.

        Returns:
            List[str]: List of installed model names
        """
        if not self._connected or not self._client:
            return []

        try:
            response = await self._client.get("/api/tags")
            response.raise_for_status()
            data = response.json()

            models = []
            if "models" in data:
                for model in data["models"]:
                    models.append(model["name"])

            return models

        except Exception as e:
            self._logger.warning(f"Failed to get installed models: {e}")
            return []

    def estimate_cost(self, request: LLMRequest) -> float:
        """
        Estimate the cost of a request (always 0 for local models).

        Args:
            request: The request to estimate cost for

        Returns:
            float: Always 0.0 for local models
        """
        # Local models are free, but we could estimate compute time
        return 0.0

    def _prepare_ollama_request(self, request: LLMRequest) -> Dict[str, Any]:
        """Prepare the request for Ollama API."""
        return {
            "model": self.config.model,
            "prompt": request.prompt,
            "stream": False,  # We'll handle streaming in the future
            "options": {
                "temperature": request.config.temperature,
                "num_predict": request.config.max_tokens,
            },
        }

    async def _process_ollama_response(
        self, response: httpx.Response, request: LLMRequest, start_time: datetime
    ) -> LLMResponse:
        """Process the Ollama API response."""
        processing_time = (datetime.now() - start_time).total_seconds()

        try:
            # Parse the response
            data = response.json()

            # Check if the response indicates an error
            if "error" in data:
                error_msg = data["error"]
                return LLMResponse(
                    content="",
                    status=LLMResponseStatus.ERROR,
                    metadata=LLMResponseMetadata(
                        provider="ollama",
                        model=self.config.model,
                        tokens_used=0,
                        cost=0.0,
                        processing_time=processing_time,
                        request_id=request.request_id,
                        response_id=None,
                        metadata={"ollama_error": error_msg},
                    ),
                    error_message=error_msg,
                    error_code="ollama_error",
                    raw_response=data,
                )

            # Extract content
            content = data.get("response", "")

            # Ollama provides token counts in the response
            prompt_eval_count = data.get("prompt_eval_count", 0)
            eval_count = data.get("eval_count", 0)
            total_tokens = prompt_eval_count + eval_count

            # If no token counts available, estimate
            if total_tokens == 0:
                input_tokens = len(request.prompt.split()) * 1.3  # Rough estimation
                output_tokens = len(content.split()) * 1.3  # Rough estimation
                total_tokens = int(input_tokens + output_tokens)

            # Cost is always 0 for local models
            cost = 0.0

            # Create metadata
            metadata = LLMResponseMetadata(
                provider="ollama",
                model=self.config.model,
                tokens_used=total_tokens,
                cost=cost,
                processing_time=processing_time,
                request_id=request.request_id,
                response_id=data.get("created_at"),
                metadata={
                    "prompt_eval_count": prompt_eval_count,
                    "eval_count": eval_count,
                    "done": data.get("done", True),
                    "context": data.get("context", []),
                    "total_duration": data.get("total_duration"),
                    "load_duration": data.get("load_duration"),
                    "prompt_eval_duration": data.get("prompt_eval_duration"),
                    "eval_duration": data.get("eval_duration"),
                },
            )

            return LLMResponse(
                content=content,
                status=LLMResponseStatus.SUCCESS,
                metadata=metadata,
                raw_response=data,
            )

        except Exception as e:
            # Handle JSON parsing errors or other processing errors
            return LLMResponse(
                content="",
                status=LLMResponseStatus.ERROR,
                metadata=LLMResponseMetadata(
                    provider="ollama",
                    model=self.config.model,
                    tokens_used=0,
                    cost=0.0,
                    processing_time=processing_time,
                    request_id=request.request_id,
                    response_id=None,
                    metadata={"processing_error": str(e)},
                ),
                error_message=f"Failed to process Ollama response: {e}",
                error_code="processing_error",
                raw_response={"raw_content": response.text},
            )

    async def _test_connection(self) -> None:
        """Test the connection with a simple request."""
        if not self._client:
            raise ConnectionError("Client not initialized")

        # Check if Ollama is running
        try:
            response = await self._client.get("/api/tags")
            response.raise_for_status()
        except httpx.ConnectError:
            raise ConnectionError("Cannot connect to Ollama. Is Ollama running?")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ConnectionError("Ollama API not found. Is Ollama running?")
            raise ConnectionError(f"Ollama API error: {e}")

    def _update_metrics(self, response: LLMResponse, start_time: datetime) -> None:
        """Update provider metrics."""
        processing_time = (datetime.now() - start_time).total_seconds()

        self.metrics.add_request(
            success=response.is_success,
            tokens=response.tokens_used,
            cost=response.cost,
            response_time=processing_time,
            provider="ollama",
            model=self.config.model,
            error_type=None if response.is_success else "api_error",
        )


# Custom exceptions for better error handling
class LLMError(Exception):
    """Base exception for LLM-related errors."""

    pass


class TimeoutError(LLMError):
    """Exception raised when request times out."""

    pass


class ConnectionError(LLMError):
    """Exception raised when connection fails."""

    pass
