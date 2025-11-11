"""
Anthropic LLM Provider for the Open Matching Engine.

This module provides an implementation of the BaseLLMProvider interface
for Anthropic's Claude models, including Claude-3, Claude-3.5, and other variants.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import anthropic
from anthropic import AsyncAnthropic

from .base import BaseLLMProvider, LLMProviderConfig, LLMProviderType
from ..models.requests import LLMRequest, LLMRequestConfig
from ..models.responses import LLMResponse, LLMResponseStatus, LLMResponseMetadata

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic LLM provider implementation for Claude models.
    
    This provider supports all Anthropic Claude models including:
    - Claude-3 Haiku
    - Claude-3 Sonnet  
    - Claude-3 Opus
    - Claude-3.5 Sonnet
    - Claude-3.5 Haiku
    """
    
    # Anthropic model pricing (per 1M tokens, as of 2024)
    MODEL_PRICING = {
        "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},  # $3/$15 per 1M tokens (current default)
        "claude-3-5-sonnet-latest": {"input": 3.0, "output": 15.0},  # $3/$15 per 1M tokens (deprecated, kept for compatibility)
        "claude-3-5-haiku-20241022": {"input": 1.0, "output": 5.0},   # $1/$5 per 1M tokens
        "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},    # $15/$75 per 1M tokens
        "claude-sonnet-4-5-20240229": {"input": 3.0, "output": 15.0},   # $3/$15 per 1M tokens
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},   # $0.25/$1.25 per 1M tokens
    }
    
    # Available models (ordered by preference)
    AVAILABLE_MODELS = [
        "claude-sonnet-4-5-20250929",  # Current default
        "claude-3-5-sonnet-latest",  # Deprecated, kept for compatibility
        "claude-3-5-haiku-20241022", 
        "claude-3-opus-20240229",
        "claude-sonnet-4-5-20240229",
        "claude-3-haiku-20240307",
    ]
    
    def __init__(self, config: LLMProviderConfig):
        """
        Initialize the Anthropic provider.
        
        Args:
            config: Configuration for the provider
            
        Raises:
            ValueError: If configuration is invalid
        """
        super().__init__(config)
        self._client: Optional[AsyncAnthropic] = None
        
        # Validate that this is an Anthropic provider
        if config.provider_type != LLMProviderType.ANTHROPIC:
            raise ValueError(f"Provider type must be ANTHROPIC, got {config.provider_type}")
    
    async def connect(self) -> None:
        """
        Connect to the Anthropic API.
        
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If API key is invalid
        """
        try:
            # Only pass parameters that AsyncAnthropic actually accepts
            client_kwargs = {
                "api_key": self.config.api_key,
            }
            
            # Add optional parameters only if they're provided
            if self.config.base_url:
                client_kwargs["base_url"] = self.config.base_url
            
            self._client = AsyncAnthropic(**client_kwargs)
            
            # Skip connection test to avoid hanging during initialization
            # The connection will be tested on the first actual request
            self._connected = True
            self._logger.info(f"Connected to Anthropic API with model {self.config.model}")
            
        except Exception as e:
            self._connected = False
            self._logger.error(f"Failed to connect to Anthropic API: {e}")
            raise ConnectionError(f"Failed to connect to Anthropic API: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from the Anthropic API."""
        if self._client:
            # Anthropic client doesn't have explicit disconnect, just clear the reference
            self._client = None
        
        self._connected = False
        self._logger.info("Disconnected from Anthropic API")
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response using Anthropic's Claude model.
        
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
            # Prepare the request for Anthropic
            anthropic_request = self._prepare_anthropic_request(request)
            
            # Make the API call
            response = await self._client.messages.create(**anthropic_request)
            
            # Process the response
            llm_response = self._process_anthropic_response(response, request, start_time)
            
            # Update metrics
            self._update_metrics(llm_response, start_time)
            
            return llm_response
            
        except anthropic.RateLimitError as e:
            self._logger.warning(f"Rate limit exceeded: {e}")
            raise RateLimitError(f"Rate limit exceeded: {e}")
            
        except anthropic.APITimeoutError as e:
            self._logger.warning(f"Request timeout: {e}")
            raise TimeoutError(f"Request timeout: {e}")
            
        except anthropic.APIError as e:
            self._logger.error(f"Anthropic API error: {e}")
            raise LLMError(f"Anthropic API error: {e}")
            
        except Exception as e:
            self._logger.error(f"Unexpected error: {e}")
            raise LLMError(f"Unexpected error: {e}")
    
    async def health_check(self) -> bool:
        """
        Check if the Anthropic provider is healthy.
        
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
        Get list of available Anthropic models.
        
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
        estimated_input_tokens = len(request.prompt.split()) * 1.3  # Rough token estimation
        estimated_output_tokens = request.config.max_tokens * 0.5   # Assume 50% of max tokens used
        
        input_cost = (estimated_input_tokens / 1_000_000) * pricing["input"]
        output_cost = (estimated_output_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost
    
    def _prepare_anthropic_request(self, request: LLMRequest) -> Dict[str, Any]:
        """Prepare the request for Anthropic API."""
        return {
            "model": self.config.model,
            "max_tokens": request.config.max_tokens,
            "temperature": request.config.temperature,
            "messages": [
                {
                    "role": "user",
                    "content": request.prompt
                }
            ]
        }
    
    def _process_anthropic_response(self, response: Any, request: LLMRequest, start_time: datetime) -> LLMResponse:
        """Process the Anthropic API response."""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Extract content from response
        content = ""
        if response.content and len(response.content) > 0:
            content = response.content[0].text
        
        # Calculate tokens used
        input_tokens = response.usage.input_tokens if response.usage else 0
        output_tokens = response.usage.output_tokens if response.usage else 0
        total_tokens = input_tokens + output_tokens
        
        # Calculate cost
        cost = self._calculate_cost(input_tokens, output_tokens)
        
        # Create metadata
        metadata = LLMResponseMetadata(
            provider="anthropic",
            model=self.config.model,
            tokens_used=total_tokens,
            cost=cost,
            processing_time=processing_time,
            request_id=request.request_id,
            response_id=response.id if hasattr(response, 'id') else None,
            metadata={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "stop_reason": response.stop_reason if hasattr(response, 'stop_reason') else None
            }
        )
        
        return LLMResponse(
            content=content,
            status=LLMResponseStatus.SUCCESS,
            metadata=metadata,
            raw_response={
                "id": response.id if hasattr(response, 'id') else None,
                "model": response.model if hasattr(response, 'model') else None,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens
                } if response.usage else None,
                "stop_reason": response.stop_reason if hasattr(response, 'stop_reason') else None
            }
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
        test_response = await self._client.messages.create(
            model=self.config.model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Hello"}]
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
            provider="anthropic",
            model=self.config.model,
            error_type=None if response.is_success else "api_error"
        )


# Custom exceptions for better error handling
class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class RateLimitError(LLMError):
    """Exception raised when rate limit is exceeded."""
    pass
