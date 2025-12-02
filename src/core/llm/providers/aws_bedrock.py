"""
AWS Bedrock LLM Provider for the Open Matching Engine.

This module provides an implementation of the BaseLLMProvider interface
for AWS Bedrock, which provides a unified API to access foundation models
from multiple providers (Anthropic Claude, Meta Llama, Amazon Titan, etc.)
through AWS infrastructure.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
import json

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from .base import BaseLLMProvider, LLMProviderConfig, LLMProviderType
from ..models.requests import LLMRequest, LLMRequestConfig
from ..models.responses import LLMResponse, LLMResponseStatus, LLMResponseMetadata

logger = logging.getLogger(__name__)


@dataclass
class AWSBedrockProviderConfig(LLMProviderConfig):
    """Configuration for AWS Bedrock provider."""

    region: str = "us-east-1"  # AWS region
    model_id: str = (
        ""  # Full model ID (e.g., "anthropic.claude-3-5-sonnet-20241022-v2:0")
    )
    use_api_key: bool = False  # Use API key vs AWS credentials
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None

    def __post_init__(self):
        """Validate AWS Bedrock specific configuration."""
        super().__post_init__()
        if not self.model_id:
            raise ValueError("model_id is required for AWS Bedrock provider")
        if self.use_api_key and not self.api_key:
            raise ValueError("api_key is required when use_api_key is True")
        if not self.use_api_key and not (
            self.aws_access_key_id and self.aws_secret_access_key
        ):
            # Allow using default AWS credentials from environment/IAM role
            pass


class AWSBedrockProvider(BaseLLMProvider):
    """
    AWS Bedrock LLM provider implementation.

    This provider supports models from multiple providers via AWS Bedrock:
    - Anthropic Claude models
    - Meta Llama models
    - Amazon Titan models
    - And more
    """

    # AWS Bedrock model pricing (per 1M tokens, examples - varies by model)
    # Note: Pricing should be verified from AWS Bedrock pricing page
    MODEL_PRICING = {
        "anthropic.claude-3-5-sonnet-20241022-v2:0": {"input": 3.0, "output": 15.0},
        "anthropic.claude-3-5-haiku-20241022-v1:0": {"input": 1.0, "output": 5.0},
        "anthropic.claude-3-opus-20240229-v1:0": {"input": 15.0, "output": 75.0},
        "meta.llama3-1-70b-instruct-v1:0": {"input": 0.65, "output": 0.65},
        "amazon.titan-text-lite-v1": {"input": 0.0003, "output": 0.0004},
    }

    # Available models (examples - actual availability depends on AWS account)
    AVAILABLE_MODELS = [
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "anthropic.claude-3-5-haiku-20241022-v1:0",
        "anthropic.claude-3-opus-20240229-v1:0",
        "meta.llama3-1-70b-instruct-v1:0",
        "amazon.titan-text-lite-v1",
    ]

    def __init__(self, config: LLMProviderConfig):
        """
        Initialize the AWS Bedrock provider.

        Args:
            config: Configuration for the provider (should be AWSBedrockProviderConfig)

        Raises:
            ValueError: If configuration is invalid
            ImportError: If boto3 is not available
        """
        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for AWS Bedrock provider. Install it with: pip install boto3"
            )

        super().__init__(config)
        self._bedrock_client: Optional[Any] = None
        self._bedrock_config: Optional[AWSBedrockProviderConfig] = None

        # Validate that this is an AWS Bedrock provider
        if config.provider_type != LLMProviderType.AWS_BEDROCK:
            raise ValueError(
                f"Provider type must be AWS_BEDROCK, got {config.provider_type}"
            )

        # Convert to Bedrock-specific config if needed
        if isinstance(config, AWSBedrockProviderConfig):
            self._bedrock_config = config
        else:
            # Try to extract Bedrock-specific fields from metadata
            metadata = config.metadata or {}
            self._bedrock_config = AWSBedrockProviderConfig(
                provider_type=config.provider_type,
                api_key=config.api_key,
                base_url=config.base_url,
                model=config.model,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                timeout=config.timeout,
                retry_attempts=config.retry_attempts,
                retry_delay=config.retry_delay,
                region=metadata.get("region", "us-east-1"),
                model_id=metadata.get("model_id", ""),
                use_api_key=metadata.get("use_api_key", False),
                aws_access_key_id=metadata.get("aws_access_key_id"),
                aws_secret_access_key=metadata.get("aws_secret_access_key"),
                aws_session_token=metadata.get("aws_session_token"),
            )

    async def connect(self) -> None:
        """
        Connect to the AWS Bedrock API.

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If credentials are invalid
        """
        try:
            # Create boto3 client
            client_kwargs = {
                "service_name": "bedrock-runtime",
                "region_name": self._bedrock_config.region,
            }

            # Add credentials if provided (otherwise use default AWS credentials)
            if not self._bedrock_config.use_api_key:
                if (
                    self._bedrock_config.aws_access_key_id
                    and self._bedrock_config.aws_secret_access_key
                ):
                    client_kwargs["aws_access_key_id"] = (
                        self._bedrock_config.aws_access_key_id
                    )
                    client_kwargs["aws_secret_access_key"] = (
                        self._bedrock_config.aws_secret_access_key
                    )
                    if self._bedrock_config.aws_session_token:
                        client_kwargs["aws_session_token"] = (
                            self._bedrock_config.aws_session_token
                        )

            self._bedrock_client = boto3.client(**client_kwargs)

            # Skip connection test to avoid hanging during initialization
            # The connection will be tested on the first actual request
            self._connected = True
            self._logger.info(
                f"Connected to AWS Bedrock in region {self._bedrock_config.region} with model {self._bedrock_config.model_id}"
            )

        except Exception as e:
            self._connected = False
            self._logger.error(f"Failed to connect to AWS Bedrock: {e}")
            raise ConnectionError(f"Failed to connect to AWS Bedrock: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the AWS Bedrock API."""
        if self._bedrock_client:
            # boto3 clients don't need explicit cleanup, but we clear the reference
            self._bedrock_client = None

        self._connected = False
        self._logger.info("Disconnected from AWS Bedrock")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response using AWS Bedrock.

        Args:
            request: The LLM request to process

        Returns:
            LLMResponse: The generated response

        Raises:
            LLMError: If the request fails
            RateLimitError: If rate limit is exceeded
            TimeoutError: If the request times out
        """
        if not self._connected or not self._bedrock_client:
            raise ConnectionError("Provider not connected")

        start_time = datetime.now()

        try:
            # Prepare the request for Bedrock Converse API
            bedrock_request = self._prepare_bedrock_request(request)

            # Make the API call using boto3
            # Note: boto3 is synchronous, so we run it in an executor
            import asyncio

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._bedrock_client.converse(
                    modelId=self._bedrock_config.model_id, **bedrock_request
                ),
            )

            # Process the response
            llm_response = self._process_bedrock_response(response, request, start_time)

            # Update metrics
            self._update_metrics(llm_response, start_time)

            return llm_response

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "ThrottlingException":
                self._logger.warning(f"Rate limit exceeded: {e}")
                raise RateLimitError(f"Rate limit exceeded: {e}")
            elif error_code in ["AccessDeniedException", "UnauthorizedException"]:
                self._logger.error(f"Authentication failed: {e}")
                raise AuthenticationError(f"Authentication failed: {e}")
            else:
                self._logger.error(f"AWS Bedrock API error: {e}")
                raise LLMError(f"AWS Bedrock API error: {e}")

        except BotoCoreError as e:
            self._logger.error(f"AWS SDK error: {e}")
            raise LLMError(f"AWS SDK error: {e}")

        except Exception as e:
            self._logger.error(f"Unexpected error: {e}")
            raise LLMError(f"Unexpected error: {e}")

    async def health_check(self) -> bool:
        """
        Check if the AWS Bedrock provider is healthy.

        Returns:
            bool: True if healthy, False otherwise
        """
        if not self._connected or not self._bedrock_client:
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
        Get list of available AWS Bedrock models.

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
        model_id = self._bedrock_config.model_id
        if model_id not in self.MODEL_PRICING:
            # Default pricing if model not found
            return 0.0

        pricing = self.MODEL_PRICING[model_id]

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

    def _prepare_bedrock_request(self, request: LLMRequest) -> Dict[str, Any]:
        """Prepare the request for AWS Bedrock Converse API."""
        # Convert messages to Bedrock format
        messages = [{"role": "user", "content": [{"text": request.prompt}]}]

        # Build inference config
        inference_config = {
            "temperature": request.config.temperature,
            "maxTokens": request.config.max_tokens,
            "topP": request.config.top_p,
        }

        bedrock_request = {
            "messages": messages,
            "inferenceConfig": inference_config,
        }

        return bedrock_request

    def _process_bedrock_response(
        self, response: Dict[str, Any], request: LLMRequest, start_time: datetime
    ) -> LLMResponse:
        """Process the AWS Bedrock API response."""
        processing_time = (datetime.now() - start_time).total_seconds()

        # Extract content from response
        content = ""
        output = response.get("output", {})
        message = output.get("message", {})
        content_parts = message.get("content", [])
        if content_parts and len(content_parts) > 0:
            content = content_parts[0].get("text", "")

        # Calculate tokens used
        usage = output.get("usage", {})
        input_tokens = usage.get("inputTokens", 0)
        output_tokens = usage.get("outputTokens", 0)
        total_tokens = usage.get("totalTokens", input_tokens + output_tokens)

        # Calculate cost
        cost = self._calculate_cost(input_tokens, output_tokens)

        # Create metadata
        metadata = LLMResponseMetadata(
            provider="aws_bedrock",
            model=self._bedrock_config.model_id,
            tokens_used=total_tokens,
            cost=cost,
            processing_time=processing_time,
            request_id=request.request_id,
            response_id=response.get("responseId"),
            metadata={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "stop_reason": output.get("stopReason"),
                "region": self._bedrock_config.region,
            },
        )

        return LLMResponse(
            content=content,
            status=LLMResponseStatus.SUCCESS,
            metadata=metadata,
            raw_response=response,
        )

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate the cost based on token usage."""
        model_id = self._bedrock_config.model_id
        if model_id not in self.MODEL_PRICING:
            return 0.0

        pricing = self.MODEL_PRICING[model_id]

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    async def _test_connection(self) -> None:
        """Test the connection with a simple request."""
        if not self._bedrock_client:
            raise ConnectionError("Client not initialized")

        # Make a minimal test request
        import asyncio

        loop = asyncio.get_event_loop()
        test_request = {
            "messages": [{"role": "user", "content": [{"text": "Hello"}]}],
            "inferenceConfig": {"maxTokens": 10},
        }

        response = await loop.run_in_executor(
            None,
            lambda: self._bedrock_client.converse(
                modelId=self._bedrock_config.model_id, **test_request
            ),
        )

        if not response:
            raise ConnectionError("Test request failed")

    def _update_metrics(self, response: LLMResponse, start_time: datetime) -> None:
        """Update provider metrics."""
        processing_time = (datetime.now() - start_time).total_seconds()

        self.metrics.add_request(
            success=response.is_success,
            tokens=response.tokens_used,
            cost=response.cost,
            response_time=processing_time,
            provider="aws_bedrock",
            model=self._bedrock_config.model_id,
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
