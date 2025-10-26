"""
Base LLM Provider Interface for the Open Matching Engine.

This module provides the abstract base class for all LLM providers,
defining the standardized interface that all providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, AsyncContextManager
from datetime import datetime
from enum import Enum
import logging

from ..models.requests import LLMRequest, LLMRequestConfig
from ..models.responses import LLMResponse, LLMResponseStatus
from ..models.metrics import LLMMetrics

logger = logging.getLogger(__name__)


class LLMProviderType(Enum):
    """Types of LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    LOCAL = "local"
    CUSTOM = "custom"


@dataclass
class LLMProviderConfig:
    """Configuration for LLM providers."""
    provider_type: LLMProviderType
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str = "claude-3-5-sonnet-20240620"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    rate_limit: Optional[int] = None
    cost_per_token: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts must be non-negative")


class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers.
    
    This class defines the standardized interface that all LLM providers
    must implement, ensuring consistent behavior across different providers.
    """
    
    def __init__(self, config: LLMProviderConfig):
        """
        Initialize the LLM provider.
        
        Args:
            config: Configuration for the provider
            
        Raises:
            ValueError: If configuration is invalid
        """
        self.config = config
        self.metrics = LLMMetrics()
        self._connected = False
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Validate configuration
        self._validate_config()
    
    @abstractmethod
    async def connect(self) -> None:
        """
        Connect to the LLM provider.
        
        This method should establish the connection to the provider's API
        and perform any necessary authentication.
        
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """
        Disconnect from the LLM provider.
        
        This method should clean up any resources and close connections.
        """
        pass
    
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response from the LLM provider.
        
        Args:
            request: The LLM request to process
            
        Returns:
            LLMResponse: The generated response
            
        Raises:
            LLMError: If the request fails
            RateLimitError: If rate limit is exceeded
            TimeoutError: If the request times out
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and available.
        
        Returns:
            bool: True if the provider is healthy, False otherwise
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        Get list of available models for this provider.
        
        Returns:
            List[str]: List of available model names
        """
        pass
    
    @abstractmethod
    def estimate_cost(self, request: LLMRequest) -> float:
        """
        Estimate the cost of a request.
        
        Args:
            request: The request to estimate cost for
            
        Returns:
            float: Estimated cost in USD
        """
        pass
    
    @property
    def is_connected(self) -> bool:
        """Check if the provider is connected."""
        return self._connected
    
    @property
    def provider_type(self) -> LLMProviderType:
        """Get the provider type."""
        return self.config.provider_type
    
    @property
    def model(self) -> str:
        """Get the current model."""
        return self.config.model
    
    def _validate_config(self) -> None:
        """Validate the provider configuration."""
        if not self.config.api_key and self.config.provider_type != LLMProviderType.LOCAL:
            raise ValueError(f"API key required for {self.config.provider_type.value} provider")
    
    async def __aenter__(self) -> "BaseLLMProvider":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()
    
    def __repr__(self) -> str:
        """String representation of the provider."""
        return f"{self.__class__.__name__}(provider={self.provider_type.value}, model={self.model})"
