"""
LLM Service for the Open Matching Engine (OME).

This service provides centralized management of LLM providers, including:
- Provider selection and routing
- Request handling and load balancing
- Fallback mechanisms and error recovery
- Cost tracking and usage analytics
- Integration with existing service patterns

The LLM service follows the BaseService pattern and provides a unified
interface for all LLM operations across the system.
"""

import asyncio
import os
from typing import Dict, List, Optional, Any, Type
from datetime import datetime


from ..services.base import BaseService, ServiceConfig, ServiceStatus
from ..utils.logging import get_logger
from .providers.base import BaseLLMProvider, LLMProviderConfig, LLMProviderType
from .providers.anthropic import AnthropicProvider
from .models.requests import LLMRequest, LLMRequestConfig, LLMRequestType
from .models.responses import LLMResponse, LLMResponseStatus


logger = get_logger(__name__)


class LLMServiceConfig(ServiceConfig):
    """Configuration for the LLM service."""
    
    def __init__(
        self,
        name: str = "LLMService",
        # Default provider settings
        default_provider: LLMProviderType = LLMProviderType.ANTHROPIC,
        default_model: str = "claude-3-5-sonnet-20241022",
        # Provider configurations
        providers: Optional[Dict[str, LLMProviderConfig]] = None,
        # Request settings
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 30,
        # Fallback settings
        enable_fallback: bool = True,
        fallback_providers: Optional[List[LLMProviderType]] = None,
        # Cost management
        max_cost_per_request: float = 1.0,  # $1.00 max per request
        enable_cost_tracking: bool = True,
        # Performance settings
        max_concurrent_requests: int = 10,
        request_queue_size: int = 100,
        **kwargs
    ):
        # Initialize base ServiceConfig
        super().__init__(
            name=name,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay,
            timeout_seconds=timeout,
            **kwargs
        )
        
        # LLM-specific settings
        self.default_provider = default_provider
        self.default_model = default_model
        self.providers = providers or {}
        self.enable_fallback = enable_fallback
        self.fallback_providers = fallback_providers or [
            LLMProviderType.ANTHROPIC,
            LLMProviderType.OPENAI,
            LLMProviderType.GOOGLE
        ]
        self.max_cost_per_request = max_cost_per_request
        self.enable_cost_tracking = enable_cost_tracking
        self.max_concurrent_requests = max_concurrent_requests
        self.request_queue_size = request_queue_size


class LLMService(BaseService['LLMService']):
    """
    Centralized LLM service for managing multiple providers.
    
    This service provides:
    - Provider management and selection
    - Request routing and load balancing
    - Fallback mechanisms and error recovery
    - Cost tracking and usage analytics
    - Integration with existing service patterns
    """
    
    def __init__(self, service_name: str = "LLMService", config: Optional[LLMServiceConfig] = None):
        """Initialize the LLM service."""
        super().__init__(service_name, config)
        self.config: LLMServiceConfig = config or LLMServiceConfig()
        
        # Provider management
        self._providers: Dict[LLMProviderType, BaseLLMProvider] = {}
        self._provider_configs: Dict[LLMProviderType, LLMProviderConfig] = {}
        self._active_provider: Optional[LLMProviderType] = None
        
        # Request management
        self._request_semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        self._request_queue: asyncio.Queue = asyncio.Queue(maxsize=self.config.request_queue_size)
        
        # Metrics and tracking
        self._total_requests: int = 0
        self._total_cost: float = 0.0
        self._request_history: List[Dict[str, Any]] = []
        
        # Provider registry
        self._provider_classes: Dict[LLMProviderType, Type[BaseLLMProvider]] = {
            LLMProviderType.ANTHROPIC: AnthropicProvider,
            # TODO: Add other providers as they're implemented
            # LLMProviderType.OPENAI: OpenAIProvider,
            # LLMProviderType.GOOGLE: GoogleProvider,
            # LLMProviderType.LOCAL: LocalProvider,
        }
    
    async def initialize(self) -> None:
        """Initialize the LLM service."""
        self.logger.info("Initializing LLM service...")
        
        # Initialize default providers
        await self._initialize_providers()
        
        # Set active provider
        self._active_provider = self.config.default_provider
        
        self.logger.info(f"LLM service initialized with {len(self._providers)} providers")
        self.logger.info(f"Active provider: {self._active_provider}")
    
    async def _initialize_dependencies(self) -> None:
        """Initialize service dependencies."""
        # No external dependencies for now
        pass
    
    async def _initialize_providers(self) -> None:
        """Initialize configured providers."""
        # Initialize default provider if not configured
        if not self.config.providers:
            # Get API key from environment
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                self.logger.error("ANTHROPIC_API_KEY not found in environment")
                return
            
            default_config = LLMProviderConfig(
                provider_type=self.config.default_provider,
                api_key=api_key,
                model=self.config.default_model
            )
            self.config.providers[self.config.default_provider.value] = default_config
        
        # Initialize each configured provider
        for provider_name, provider_config in self.config.providers.items():
            try:
                provider_type = provider_config.provider_type
                
                if provider_type not in self._provider_classes:
                    self.logger.warning(f"Provider {provider_type} not implemented, skipping")
                    continue
                
                # Create provider instance
                provider_class = self._provider_classes[provider_type]
                provider = provider_class(provider_config)
                
                # Connect to provider
                await provider.connect()
                
                # Store provider
                self._providers[provider_type] = provider
                self._provider_configs[provider_type] = provider_config
                
                self.logger.info(f"Initialized provider: {provider_type}")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize provider {provider_name}: {e}")
                # Continue with other providers
    
    async def generate(
        self,
        prompt: str,
        request_type: LLMRequestType = LLMRequestType.GENERATION,
        config: Optional[LLMRequestConfig] = None,
        provider: Optional[LLMProviderType] = None
    ) -> LLMResponse:
        """
        Generate a response using the specified or default provider.
        
        Args:
            prompt: The input prompt
            request_type: Type of request (generation, matching, etc.)
            config: Request configuration
            provider: Specific provider to use (optional)
            
        Returns:
            LLMResponse with the generated content
            
        Raises:
            LLMError: If generation fails
        """
        async with self._request_semaphore:
            return await self._generate_with_fallback(prompt, request_type, config, provider)
    
    async def _generate_with_fallback(
        self,
        prompt: str,
        request_type: LLMRequestType,
        config: Optional[LLMRequestConfig],
        provider: Optional[LLMProviderType]
    ) -> LLMResponse:
        """Generate with fallback mechanism."""
        # Determine which providers to try
        providers_to_try = self._get_providers_to_try(provider)
        
        last_error = None
        
        for provider_type in providers_to_try:
            try:
                if provider_type not in self._providers:
                    self.logger.warning(f"Provider {provider_type} not available, skipping")
                    continue
                
                # Create request
                request = LLMRequest(
                    prompt=prompt,
                    request_type=request_type,
                    config=config or LLMRequestConfig()
                )
                
                # Check cost limits
                if self.config.enable_cost_tracking:
                    estimated_cost = self._providers[provider_type].estimate_cost(request)
                    if estimated_cost > self.config.max_cost_per_request:
                        self.logger.warning(f"Request cost ${estimated_cost:.4f} exceeds limit ${self.config.max_cost_per_request}")
                        continue
                
                # Generate response
                response = await self._providers[provider_type].generate(request)
                
                # Update metrics
                self._update_metrics(response, provider_type)
                
                # Return successful response
                return response
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"Provider {provider_type} failed: {e}")
                
                # Update error metrics
                self.metrics.errors.append(f"Provider {provider_type} failed: {str(e)}")
                
                # Continue to next provider if fallback is enabled
                if not self.config.enable_fallback:
                    break
        
        # All providers failed
        error_msg = f"All providers failed. Last error: {last_error}"
        self.logger.error(error_msg)
        
        from .models.responses import LLMResponseMetadata
        
        error_metadata = LLMResponseMetadata(
            provider=provider.value if provider else "unknown",
            model="unknown",
            tokens_used=0,
            cost=0.0,
            processing_time=0.0
        )
        
        return LLMResponse(
            content="",
            status=LLMResponseStatus.ERROR,
            metadata=error_metadata,
            error_message=error_msg
        )
    
    def _get_providers_to_try(self, preferred_provider: Optional[LLMProviderType]) -> List[LLMProviderType]:
        """Get list of providers to try in order."""
        if preferred_provider:
            # Try preferred provider first, then fallbacks
            providers = [preferred_provider]
            for fallback in self.config.fallback_providers:
                if fallback != preferred_provider and fallback not in providers:
                    providers.append(fallback)
        else:
            # Use active provider first, then fallbacks
            providers = [self._active_provider] if self._active_provider else []
            for fallback in self.config.fallback_providers:
                if fallback not in providers:
                    providers.append(fallback)
        
        return providers
    
    def _update_metrics(self, response: LLMResponse, provider_type: LLMProviderType) -> None:
        """Update service metrics."""
        self._total_requests += 1
        self._total_cost += response.cost
        
        # Add to request history
        self._request_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "provider": provider_type.value,
            "model": response.metadata.model,
            "tokens_used": response.tokens_used,
            "cost": response.cost,
            "status": response.status.value
        })
        
        # Keep only last 1000 requests in history
        if len(self._request_history) > 1000:
            self._request_history = self._request_history[-1000:]
    
    async def get_available_providers(self) -> List[LLMProviderType]:
        """Get list of available providers."""
        return list(self._providers.keys())
    
    async def get_provider_status(self, provider_type: LLMProviderType) -> Dict[str, Any]:
        """Get status information for a specific provider."""
        if provider_type not in self._providers:
            return {"status": "not_available", "error": "Provider not initialized"}
        
        provider = self._providers[provider_type]
        
        try:
            is_healthy = await provider.health_check()
            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "model": provider.config.model,
                "is_connected": provider.is_connected,
                "available_models": provider.get_available_models()
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_service_metrics(self) -> Dict[str, Any]:
        """Get comprehensive service metrics."""
        return {
            "total_requests": self._total_requests,
            "total_cost": self._total_cost,
            "average_cost_per_request": self._total_cost / max(self._total_requests, 1),
            "active_provider": self._active_provider.value if self._active_provider else None,
            "available_providers": [p.value for p in self._providers.keys()],
            "provider_status": {
                provider.value: await self.get_provider_status(provider)
                for provider in self._providers.keys()
            },
            "recent_requests": self._request_history[-10:] if self._request_history else []
        }
    
    async def set_active_provider(self, provider_type: LLMProviderType) -> bool:
        """Set the active provider."""
        if provider_type not in self._providers:
            self.logger.error(f"Provider {provider_type} not available")
            return False
        
        self._active_provider = provider_type
        self.logger.info(f"Active provider set to: {provider_type}")
        return True
    
    async def add_provider(self, provider_config: LLMProviderConfig) -> bool:
        """Add a new provider to the service."""
        try:
            provider_type = provider_config.provider_type
            
            if provider_type not in self._provider_classes:
                self.logger.error(f"Provider {provider_type} not implemented")
                return False
            
            # Create and initialize provider
            provider_class = self._provider_classes[provider_type]
            provider = provider_class(provider_config)
            await provider.connect()
            
            # Add to service
            self._providers[provider_type] = provider
            self._provider_configs[provider_type] = provider_config
            
            self.logger.info(f"Added provider: {provider_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add provider {provider_config.provider_type}: {e}")
            return False
    
    async def remove_provider(self, provider_type: LLMProviderType) -> bool:
        """Remove a provider from the service."""
        if provider_type not in self._providers:
            return False
        
        try:
            # Disconnect provider
            provider = self._providers[provider_type]
            await provider.disconnect()
            
            # Remove from service
            del self._providers[provider_type]
            del self._provider_configs[provider_type]
            
            # Update active provider if necessary
            if self._active_provider == provider_type:
                self._active_provider = next(iter(self._providers.keys()), None)
            
            self.logger.info(f"Removed provider: {provider_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove provider {provider_type}: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the LLM service."""
        self.logger.info("Shutting down LLM service...")
        
        # Disconnect all providers
        for provider_type, provider in self._providers.items():
            try:
                await provider.disconnect()
                self.logger.info(f"Disconnected provider: {provider_type}")
            except Exception as e:
                self.logger.error(f"Error disconnecting provider {provider_type}: {e}")
        
        # Clear providers
        self._providers.clear()
        self._provider_configs.clear()
        
        self.status = ServiceStatus.SHUTDOWN
        self.logger.info("LLM service shutdown complete")
