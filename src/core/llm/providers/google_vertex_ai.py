"""
Google Cloud Vertex AI LLM Provider for the Open Matching Engine.

This module provides an implementation of the BaseLLMProvider interface
for Google Cloud Vertex AI, which provides access to Google's Gemini models
and other foundation models through Google Cloud's unified ML platform.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
import json
import os

try:
    from google.cloud import aiplatform
    from google.oauth2 import service_account
    from google.auth import default as google_auth_default
    from google.auth.exceptions import GoogleAuthError
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False

from .base import BaseLLMProvider, LLMProviderConfig, LLMProviderType
from ..models.requests import LLMRequest, LLMRequestConfig
from ..models.responses import LLMResponse, LLMResponseStatus, LLMResponseMetadata

logger = logging.getLogger(__name__)


@dataclass
class GoogleVertexAIProviderConfig(LLMProviderConfig):
    """Configuration for Google Vertex AI provider."""
    project_id: str = ""  # Google Cloud project ID
    location: str = "us-central1"  # Region/location
    service_account_json: Optional[str] = None  # Path to JSON key file
    service_account_info: Optional[Dict[str, Any]] = None  # Service account dict
    model_id: str = "gemini-1.5-pro"  # Model identifier
    
    def __post_init__(self):
        """Validate Google Vertex AI specific configuration."""
        super().__post_init__()
        if not self.project_id:
            raise ValueError("project_id is required for Google Vertex AI provider")
        if not self.model_id:
            raise ValueError("model_id is required for Google Vertex AI provider")


class GoogleVertexAIProvider(BaseLLMProvider):
    """
    Google Cloud Vertex AI LLM provider implementation for Gemini models.
    
    This provider supports Google's Gemini models including:
    - gemini-1.5-pro
    - gemini-1.5-flash
    - gemini-pro
    - gemini-pro-vision
    """
    
    # Google Vertex AI model pricing (per 1M tokens, examples - varies by model and region)
    # Note: Pricing should be verified from Google Cloud Vertex AI pricing page
    MODEL_PRICING = {
        "gemini-1.5-pro": {"input": 1.25, "output": 5.0},  # $1.25/$5 per 1M tokens
        "gemini-1.5-flash": {"input": 0.075, "output": 0.3},  # $0.075/$0.3 per 1M tokens
        "gemini-pro": {"input": 0.5, "output": 1.5},  # $0.5/$1.5 per 1M tokens
        "gemini-pro-vision": {"input": 0.25, "output": 1.0},  # $0.25/$1 per 1M tokens
    }
    
    # Available models
    AVAILABLE_MODELS = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro",
        "gemini-pro-vision",
    ]
    
    def __init__(self, config: LLMProviderConfig):
        """
        Initialize the Google Vertex AI provider.
        
        Args:
            config: Configuration for the provider (should be GoogleVertexAIProviderConfig)
            
        Raises:
            ValueError: If configuration is invalid
            ImportError: If google-cloud-aiplatform is not available
        """
        if not GOOGLE_CLOUD_AVAILABLE:
            raise ImportError(
                "google-cloud-aiplatform and google-auth are required for Google Vertex AI provider. "
                "Install them with: pip install google-cloud-aiplatform google-auth"
            )
        
        super().__init__(config)
        self._vertex_client: Optional[Any] = None
        self._credentials: Optional[Any] = None
        self._vertex_config: Optional[GoogleVertexAIProviderConfig] = None
        
        # Validate that this is a Google provider
        if config.provider_type != LLMProviderType.GOOGLE:
            raise ValueError(f"Provider type must be GOOGLE, got {config.provider_type}")
        
        # Convert to Vertex AI-specific config if needed
        if isinstance(config, GoogleVertexAIProviderConfig):
            self._vertex_config = config
        else:
            # Try to extract Vertex AI-specific fields from metadata
            metadata = config.metadata or {}
            self._vertex_config = GoogleVertexAIProviderConfig(
                provider_type=config.provider_type,
                api_key=config.api_key,  # Not used for Vertex AI, but kept for compatibility
                base_url=config.base_url,  # Not used for Vertex AI
                model=config.model,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                timeout=config.timeout,
                retry_attempts=config.retry_attempts,
                retry_delay=config.retry_delay,
                project_id=metadata.get("project_id", ""),
                location=metadata.get("location", "us-central1"),
                service_account_json=metadata.get("service_account_json"),
                service_account_info=metadata.get("service_account_info"),
                model_id=metadata.get("model_id", "gemini-1.5-pro"),
            )
    
    async def connect(self) -> None:
        """
        Connect to the Google Vertex AI API.
        
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If credentials are invalid
        """
        try:
            # Initialize credentials
            self._credentials = await self._get_credentials()
            
            # Initialize Vertex AI
            aiplatform.init(
                project=self._vertex_config.project_id,
                location=self._vertex_config.location,
                credentials=self._credentials,
            )
            
            # Create Vertex AI client (using the REST API via httpx would be more async-friendly,
            # but we'll use the SDK for now and run it in executor)
            self._connected = True
            self._logger.info(
                f"Connected to Google Vertex AI in project {self._vertex_config.project_id}, "
                f"location {self._vertex_config.location} with model {self._vertex_config.model_id}"
            )
            
        except GoogleAuthError as e:
            self._connected = False
            self._logger.error(f"Failed to authenticate with Google Cloud: {e}")
            raise AuthenticationError(f"Failed to authenticate with Google Cloud: {e}")
        except Exception as e:
            self._connected = False
            self._logger.error(f"Failed to connect to Google Vertex AI: {e}")
            raise ConnectionError(f"Failed to connect to Google Vertex AI: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from the Google Vertex AI API."""
        # Vertex AI doesn't require explicit cleanup
        self._vertex_client = None
        self._credentials = None
        self._connected = False
        self._logger.info("Disconnected from Google Vertex AI")
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response using Google Vertex AI's Gemini model.
        
        Args:
            request: The LLM request to process
            
        Returns:
            LLMResponse: The generated response
            
        Raises:
            LLMError: If the request fails
            RateLimitError: If rate limit is exceeded
            TimeoutError: If the request times out
        """
        if not self._connected:
            raise ConnectionError("Provider not connected")
        
        start_time = datetime.now()
        
        try:
            # Prepare the request for Vertex AI
            vertex_request = self._prepare_vertex_request(request)
            
            # Make the API call using Vertex AI SDK
            # Note: The SDK is synchronous, so we run it in an executor
            import asyncio
            import httpx
            
            # Build the endpoint URL
            endpoint = (
                f"https://{self._vertex_config.location}-aiplatform.googleapis.com"
                f"/v1/projects/{self._vertex_config.project_id}"
                f"/locations/{self._vertex_config.location}"
                f"/publishers/google/models/{self._vertex_config.model_id}:generateContent"
            )
            
            # Get access token
            if self._credentials:
                # Refresh credentials if needed
                from google.auth.transport.requests import Request as GoogleAuthRequest
                if not self._credentials.valid:
                    self._credentials.refresh(GoogleAuthRequest())
                token = self._credentials.token
            else:
                raise AuthenticationError("No credentials available")
            
            # Make async HTTP request
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    endpoint,
                    json=vertex_request,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    }
                )
                response.raise_for_status()
                response_data = response.json()
            
            # Process the response
            llm_response = self._process_vertex_response(response_data, request, start_time)
            
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
                self._logger.error(f"Google Vertex AI API error: {e}")
                raise LLMError(f"Google Vertex AI API error: {e}")
            
        except httpx.TimeoutException as e:
            self._logger.warning(f"Request timeout: {e}")
            raise TimeoutError(f"Request timeout: {e}")
            
        except Exception as e:
            self._logger.error(f"Unexpected error: {e}")
            raise LLMError(f"Unexpected error: {e}")
    
    async def health_check(self) -> bool:
        """
        Check if the Google Vertex AI provider is healthy.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        if not self._connected:
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
        Get list of available Google Vertex AI models.
        
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
        model_id = self._vertex_config.model_id
        if model_id not in self.MODEL_PRICING:
            # Default pricing if model not found
            return 0.0
        
        pricing = self.MODEL_PRICING[model_id]
        
        # Rough estimation based on prompt length
        # This is a simplified estimation - actual tokenization would be more accurate
        estimated_input_tokens = len(request.prompt.split()) * 1.3  # Rough token estimation
        estimated_output_tokens = request.config.max_tokens * 0.5   # Assume 50% of max tokens used
        
        input_cost = (estimated_input_tokens / 1_000_000) * pricing["input"]
        output_cost = (estimated_output_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost
    
    async def _get_credentials(self):
        """Get Google Cloud credentials."""
        # Try service account JSON file first
        if self._vertex_config.service_account_json:
            if os.path.exists(self._vertex_config.service_account_json):
                return service_account.Credentials.from_service_account_file(
                    self._vertex_config.service_account_json
                )
            else:
                raise ValueError(f"Service account file not found: {self._vertex_config.service_account_json}")
        
        # Try service account info dict
        if self._vertex_config.service_account_info:
            return service_account.Credentials.from_service_account_info(
                self._vertex_config.service_account_info
            )
        
        # Try environment variable
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if credentials_path and os.path.exists(credentials_path):
            return service_account.Credentials.from_service_account_file(credentials_path)
        
        # Try default credentials (from environment, gcloud, or metadata server)
        try:
            credentials, _ = google_auth_default()
            return credentials
        except Exception as e:
            raise AuthenticationError(
                "No valid Google Cloud credentials found. "
                "Please provide service_account_json, service_account_info, "
                "or set GOOGLE_APPLICATION_CREDENTIALS environment variable."
            ) from e
    
    def _prepare_vertex_request(self, request: LLMRequest) -> Dict[str, Any]:
        """Prepare the request for Google Vertex AI Gemini API."""
        # Convert prompt to Vertex AI format
        contents = [
            {
                "role": "user",
                "parts": [{"text": request.prompt}]
            }
        ]
        
        # Build generation config
        generation_config = {
            "temperature": request.config.temperature,
            "maxOutputTokens": request.config.max_tokens,
            "topP": request.config.top_p,
            "topK": 40,  # Default topK for Gemini
        }
        
        vertex_request = {
            "contents": contents,
            "generationConfig": generation_config,
        }
        
        return vertex_request
    
    def _process_vertex_response(self, response_data: Dict[str, Any], request: LLMRequest, start_time: datetime) -> LLMResponse:
        """Process the Google Vertex AI API response."""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Extract content from response
        content = ""
        candidates = response_data.get("candidates", [])
        if candidates and len(candidates) > 0:
            candidate = candidates[0]
            candidate_content = candidate.get("content", {})
            parts = candidate_content.get("parts", [])
            if parts and len(parts) > 0:
                content = parts[0].get("text", "")
        
        # Calculate tokens used
        usage_metadata = response_data.get("usageMetadata", {})
        input_tokens = usage_metadata.get("promptTokenCount", 0)
        output_tokens = usage_metadata.get("candidatesTokenCount", 0)
        total_tokens = usage_metadata.get("totalTokenCount", input_tokens + output_tokens)
        
        # Calculate cost
        cost = self._calculate_cost(input_tokens, output_tokens)
        
        # Create metadata
        metadata = LLMResponseMetadata(
            provider="google_vertex_ai",
            model=self._vertex_config.model_id,
            tokens_used=total_tokens,
            cost=cost,
            processing_time=processing_time,
            request_id=request.request_id,
            response_id=response_data.get("modelVersion"),
            metadata={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "finish_reason": candidates[0].get("finishReason") if candidates else None,
                "safety_ratings": candidates[0].get("safetyRatings") if candidates else None,
                "project_id": self._vertex_config.project_id,
                "location": self._vertex_config.location,
            }
        )
        
        return LLMResponse(
            content=content,
            status=LLMResponseStatus.SUCCESS,
            metadata=metadata,
            raw_response=response_data
        )
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate the cost based on token usage."""
        model_id = self._vertex_config.model_id
        if model_id not in self.MODEL_PRICING:
            return 0.0
        
        pricing = self.MODEL_PRICING[model_id]
        
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost
    
    async def _test_connection(self) -> None:
        """Test the connection with a simple request."""
        if not self._connected:
            raise ConnectionError("Provider not connected")
        
        # Make a minimal test request
        import httpx
        
        endpoint = (
            f"https://{self._vertex_config.location}-aiplatform.googleapis.com"
            f"/v1/projects/{self._vertex_config.project_id}"
            f"/locations/{self._vertex_config.location}"
            f"/publishers/google/models/{self._vertex_config.model_id}:generateContent"
        )
        
        test_request = {
            "contents": [{"role": "user", "parts": [{"text": "Hello"}]}],
            "generationConfig": {"maxOutputTokens": 10},
        }
        
        if self._credentials:
            # Refresh credentials if needed
            from google.auth.transport.requests import Request as GoogleAuthRequest
            if not self._credentials.valid:
                self._credentials.refresh(GoogleAuthRequest())
            token = self._credentials.token
        else:
            raise AuthenticationError("No credentials available")
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                endpoint,
                json=test_request,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }
            )
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
            provider="google_vertex_ai",
            model=self._vertex_config.model_id,
            error_type=None if response.is_success else "api_error"
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

