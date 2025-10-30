"""
Unit tests for the LLM Service.

This module tests the LLM service functionality including:
- Service initialization and configuration
- Provider management and selection
- Request handling and routing
- Fallback mechanisms
- Cost tracking and metrics
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any

from src.core.llm.service import LLMService, LLMServiceConfig
from src.core.llm.providers.base import LLMProviderConfig, LLMProviderType
from src.core.llm.models.requests import LLMRequest, LLMRequestConfig, LLMRequestType
from src.core.llm.models.responses import LLMResponse, LLMResponseStatus, LLMResponseMetadata
from src.core.llm.providers.anthropic import AnthropicProvider


class TestLLMService:
    """Test cases for the LLM Service."""
    
    @pytest.fixture
    def mock_anthropic_provider(self):
        """Create a mock Anthropic provider."""
        provider = Mock(spec=AnthropicProvider)
        provider.config = Mock()
        provider.config.model = "claude-3-5-sonnet-latest"
        provider.is_connected = True
        provider.connect = AsyncMock()
        provider.disconnect = AsyncMock()
        provider.health_check = AsyncMock(return_value=True)
        provider.generate = AsyncMock()
        provider.estimate_cost = Mock(return_value=0.001)
        provider.get_available_models = Mock(return_value=["claude-3-5-sonnet-latest"])
        return provider
    
    @pytest.fixture
    def service_config(self):
        """Create a test service configuration."""
        return LLMServiceConfig(
            name="test-llm-service",
            default_provider=LLMProviderType.ANTHROPIC,
            default_model="claude-3-5-sonnet-latest",
            max_retries=3,
            retry_delay=0.1,  # Fast for testing
            timeout=10,
            enable_fallback=True,
            max_cost_per_request=1.0,
            enable_cost_tracking=True,
            max_concurrent_requests=5
        )
    
    @pytest.fixture
    def llm_service(self, service_config, mock_anthropic_provider):
        """Create a test LLM service."""
        service = LLMService("test-service", service_config)
        
        # Mock the provider initialization
        with patch.object(service, '_initialize_providers') as mock_init:
            mock_init.return_value = None
            service._providers[LLMProviderType.ANTHROPIC] = mock_anthropic_provider
            service._provider_configs[LLMProviderType.ANTHROPIC] = LLMProviderConfig(
                provider_type=LLMProviderType.ANTHROPIC,
                model="claude-3-5-sonnet-latest"
            )
            service._active_provider = LLMProviderType.ANTHROPIC
            service.status = ServiceStatus.ACTIVE  # Mock as initialized
        
        return service
    
    def test_service_initialization(self, service_config):
        """Test service initialization."""
        service = LLMService("test-service", service_config)
        
        assert service.service_name == "test-service"
        assert service.config == service_config
        assert service._active_provider is None
        assert len(service._providers) == 0
        assert service._total_requests == 0
        assert service._total_cost == 0.0
    
    def test_service_config_defaults(self):
        """Test service configuration defaults."""
        config = LLMServiceConfig()
        
        assert config.default_provider == LLMProviderType.ANTHROPIC
        assert config.default_model == "claude-3-5-sonnet-latest"
        assert config.max_retries == 3
        assert config.retry_delay_seconds == 1.0
        assert config.timeout_seconds == 30
        assert config.enable_fallback is True
        assert config.max_cost_per_request == 1.0
        assert config.enable_cost_tracking is True
        assert config.max_concurrent_requests == 10
    
    @pytest.mark.asyncio
    async def test_generate_success(self, llm_service, mock_anthropic_provider):
        """Test successful generation."""
        # Mock successful response
        mock_metadata = LLMResponseMetadata(
            provider="anthropic",
            model="claude-3-5-sonnet-latest",
            tokens_used=10,
            cost=0.001,
            processing_time=1.0
        )
        mock_response = LLMResponse(
            content="Test response",
            status=LLMResponseStatus.SUCCESS,
            metadata=mock_metadata
        )
        mock_anthropic_provider.generate.return_value = mock_response
        
        # Test generation
        response = await llm_service.generate("Test prompt")
        
        assert response.status == LLMResponseStatus.SUCCESS
        assert response.content == "Test response"
        assert response.cost == 0.001
        
        # Verify provider was called
        mock_anthropic_provider.generate.assert_called_once()
        
        # Verify metrics were updated
        assert llm_service._total_requests == 1
        assert llm_service._total_cost == 0.001
    
    @pytest.mark.asyncio
    async def test_generate_with_custom_config(self, llm_service, mock_anthropic_provider):
        """Test generation with custom request configuration."""
        # Mock successful response
        mock_response = LLMResponse(
            content="Custom response",
            status=LLMResponseStatus.SUCCESS,
            provider="anthropic",
            model="claude-3-5-sonnet-latest",
            tokens_used=20,
            cost=0.002
        )
        mock_anthropic_provider.generate.return_value = mock_response
        
        # Custom request config
        request_config = LLMRequestConfig(
            max_tokens=100,
            temperature=0.8
        )
        
        # Test generation
        response = await llm_service.generate(
            "Test prompt",
            request_type=LLMRequestType.MATCHING,
            config=request_config
        )
        
        assert response.status == LLMResponseStatus.SUCCESS
        assert response.content == "Custom response"
        
        # Verify the request was created with custom config
        call_args = mock_anthropic_provider.generate.call_args[0][0]
        assert call_args.config.max_tokens == 100
        assert call_args.config.temperature == 0.8
        assert call_args.request_type == LLMRequestType.MATCHING
    
    @pytest.mark.asyncio
    async def test_generate_with_specific_provider(self, llm_service, mock_anthropic_provider):
        """Test generation with specific provider."""
        # Mock successful response
        mock_response = LLMResponse(
            content="Provider-specific response",
            status=LLMResponseStatus.SUCCESS,
            provider="anthropic",
            model="claude-3-5-sonnet-latest",
            tokens_used=15,
            cost=0.0015
        )
        mock_anthropic_provider.generate.return_value = mock_response
        
        # Test generation with specific provider
        response = await llm_service.generate(
            "Test prompt",
            provider=LLMProviderType.ANTHROPIC
        )
        
        assert response.status == LLMResponseStatus.SUCCESS
        assert response.content == "Provider-specific response"
        
        # Verify provider was called
        mock_anthropic_provider.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_cost_limit_exceeded(self, llm_service, mock_anthropic_provider):
        """Test generation when cost limit is exceeded."""
        # Mock high cost estimation
        mock_anthropic_provider.estimate_cost.return_value = 2.0  # Exceeds $1.0 limit
        
        # Test generation
        response = await llm_service.generate("Test prompt")
        
        # Should return error response
        assert response.status == LLMResponseStatus.ERROR
        assert "All providers failed" in response.error_message
        
        # Provider should not be called due to cost limit
        mock_anthropic_provider.generate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_generate_provider_failure(self, llm_service, mock_anthropic_provider):
        """Test generation when provider fails."""
        # Mock provider failure
        mock_anthropic_provider.generate.side_effect = Exception("Provider error")
        
        # Test generation
        response = await llm_service.generate("Test prompt")
        
        # Should return error response
        assert response.status == LLMResponseStatus.ERROR
        assert "All providers failed" in response.error_message
        
        # Verify provider was called
        mock_anthropic_provider.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_available_providers(self, llm_service):
        """Test getting available providers."""
        providers = await llm_service.get_available_providers()
        
        assert LLMProviderType.ANTHROPIC in providers
        assert len(providers) == 1
    
    @pytest.mark.asyncio
    async def test_get_provider_status(self, llm_service, mock_anthropic_provider):
        """Test getting provider status."""
        status = await llm_service.get_provider_status(LLMProviderType.ANTHROPIC)
        
        assert status["status"] == "healthy"
        assert status["model"] == "claude-3-5-sonnet-latest"
        assert status["is_connected"] is True
        assert "claude-3-5-sonnet-latest" in status["available_models"]
    
    @pytest.mark.asyncio
    async def test_get_provider_status_not_available(self, llm_service):
        """Test getting status for unavailable provider."""
        status = await llm_service.get_provider_status(LLMProviderType.OPENAI)
        
        assert status["status"] == "not_available"
        assert "Provider not initialized" in status["error"]
    
    @pytest.mark.asyncio
    async def test_get_service_metrics(self, llm_service, mock_anthropic_provider):
        """Test getting service metrics."""
        # Generate a request to populate metrics
        mock_response = LLMResponse(
            content="Test response",
            status=LLMResponseStatus.SUCCESS,
            provider="anthropic",
            model="claude-3-5-sonnet-latest",
            tokens_used=10,
            cost=0.001
        )
        mock_anthropic_provider.generate.return_value = mock_response
        
        await llm_service.generate("Test prompt")
        
        # Get metrics
        metrics = await llm_service.get_service_metrics()
        
        assert metrics["total_requests"] == 1
        assert metrics["total_cost"] == 0.001
        assert metrics["average_cost_per_request"] == 0.001
        assert metrics["active_provider"] == "anthropic"
        assert "anthropic" in metrics["available_providers"]
        assert len(metrics["recent_requests"]) == 1
    
    @pytest.mark.asyncio
    async def test_set_active_provider(self, llm_service):
        """Test setting active provider."""
        # Test with available provider
        success = await llm_service.set_active_provider(LLMProviderType.ANTHROPIC)
        assert success is True
        assert llm_service._active_provider == LLMProviderType.ANTHROPIC
        
        # Test with unavailable provider
        success = await llm_service.set_active_provider(LLMProviderType.OPENAI)
        assert success is False
        assert llm_service._active_provider == LLMProviderType.ANTHROPIC  # Should remain unchanged
    
    @pytest.mark.asyncio
    async def test_add_provider(self, llm_service):
        """Test adding a new provider."""
        # This test would require mocking the provider class registration
        # For now, we'll test the error case
        provider_config = LLMProviderConfig(
            provider_type=LLMProviderType.OPENAI,  # Not implemented
            model="gpt-4"
        )
        
        success = await llm_service.add_provider(provider_config)
        assert success is False  # Should fail because OpenAI provider not implemented
    
    @pytest.mark.asyncio
    async def test_remove_provider(self, llm_service, mock_anthropic_provider):
        """Test removing a provider."""
        # Test removing available provider
        success = await llm_service.remove_provider(LLMProviderType.ANTHROPIC)
        assert success is True
        assert LLMProviderType.ANTHROPIC not in llm_service._providers
        assert llm_service._active_provider is None
        
        # Verify disconnect was called
        mock_anthropic_provider.disconnect.assert_called_once()
        
        # Test removing unavailable provider
        success = await llm_service.remove_provider(LLMProviderType.OPENAI)
        assert success is False
    
    @pytest.mark.asyncio
    async def test_shutdown(self, llm_service, mock_anthropic_provider):
        """Test service shutdown."""
        await llm_service.shutdown()
        
        # Verify all providers were disconnected
        mock_anthropic_provider.disconnect.assert_called_once()
        
        # Verify providers were cleared
        assert len(llm_service._providers) == 0
        assert len(llm_service._provider_configs) == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, llm_service, mock_anthropic_provider):
        """Test handling concurrent requests."""
        # Mock successful responses
        mock_response = LLMResponse(
            content="Concurrent response",
            status=LLMResponseStatus.SUCCESS,
            provider="anthropic",
            model="claude-3-5-sonnet-latest",
            tokens_used=10,
            cost=0.001
        )
        mock_anthropic_provider.generate.return_value = mock_response
        
        # Create multiple concurrent requests
        tasks = [
            llm_service.generate(f"Test prompt {i}")
            for i in range(3)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for response in responses:
            assert response.status == LLMResponseStatus.SUCCESS
            assert response.content == "Concurrent response"
        
        # Verify metrics
        assert llm_service._total_requests == 3
        assert llm_service._total_cost == 0.003
    
    def test_provider_registry(self, service_config):
        """Test provider class registry."""
        service = LLMService("test-service", service_config)
        
        # Check that Anthropic provider is registered
        assert LLMProviderType.ANTHROPIC in service._provider_classes
        assert service._provider_classes[LLMProviderType.ANTHROPIC] == AnthropicProvider
        
        # Check that other providers are not yet implemented
        assert LLMProviderType.OPENAI not in service._provider_classes
        assert LLMProviderType.GOOGLE not in service._provider_classes
