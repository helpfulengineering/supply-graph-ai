"""
Unit tests for the Anthropic LLM provider.

This module tests the Anthropic provider implementation to ensure
it works correctly with the base provider interface.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.core.llm.providers.anthropic import AnthropicProvider
from src.core.llm.providers.base import LLMProviderConfig, LLMProviderType
from src.core.llm.models.requests import LLMRequest, LLMRequestConfig, LLMRequestType
from src.core.llm.models.responses import LLMResponseStatus


class TestAnthropicProvider:
    """Test Anthropic provider implementation."""
    
    def test_provider_initialization(self):
        """Test provider initialization."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.ANTHROPIC,
            api_key="test-key",
            model="claude-3-5-sonnet-latest"
        )
        
        provider = AnthropicProvider(config)
        
        assert provider.provider_type == LLMProviderType.ANTHROPIC
        assert provider.model == "claude-3-5-sonnet-latest"
        assert provider.is_connected is False
    
    def test_wrong_provider_type(self):
        """Test initialization with wrong provider type."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.OPENAI,  # Wrong type
            api_key="test-key"
        )
        
        with pytest.raises(ValueError, match="Provider type must be ANTHROPIC"):
            AnthropicProvider(config)
    
    def test_available_models(self):
        """Test getting available models."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.ANTHROPIC,
            api_key="test-key"
        )
        
        provider = AnthropicProvider(config)
        models = provider.get_available_models()
        
        expected_models = [
            "claude-3-5-sonnet-latest",
            "claude-3-5-haiku-20241022", 
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]
        
        assert models == expected_models
    
    def test_estimate_cost(self):
        """Test cost estimation."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.ANTHROPIC,
            api_key="test-key",
            model="claude-3-5-sonnet-latest"
        )
        
        provider = AnthropicProvider(config)
        
        request_config = LLMRequestConfig(max_tokens=1000)
        request = LLMRequest(
            prompt="Test prompt with some words",
            request_type=LLMRequestType.GENERATION,
            config=request_config
        )
        
        cost = provider.estimate_cost(request)
        assert cost > 0  # Should be a positive cost
        assert isinstance(cost, float)
    
    def test_estimate_cost_unknown_model(self):
        """Test cost estimation for unknown model."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.ANTHROPIC,
            api_key="test-key",
            model="unknown-model"
        )
        
        provider = AnthropicProvider(config)
        
        request_config = LLMRequestConfig()
        request = LLMRequest(
            prompt="Test prompt",
            request_type=LLMRequestType.GENERATION,
            config=request_config
        )
        
        cost = provider.estimate_cost(request)
        assert cost == 0.0  # Should be 0 for unknown model
    
    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.ANTHROPIC,
            api_key="test-key"
        )
        
        provider = AnthropicProvider(config)
        
        # Mock the Anthropic client and its methods
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Hello")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)
        mock_response.id = "test-id"
        mock_response.stop_reason = "end_turn"
        
        mock_client.messages.create.return_value = mock_response
        
        with patch('src.core.llm.providers.anthropic.AsyncAnthropic', return_value=mock_client):
            await provider.connect()
            
            assert provider.is_connected is True
            assert provider._client is not None
    
    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.ANTHROPIC,
            api_key="invalid-key"
        )
        
        provider = AnthropicProvider(config)
        
        # Mock the Anthropic client to raise an exception
        with patch('src.core.llm.providers.anthropic.AsyncAnthropic') as mock_anthropic:
            mock_anthropic.side_effect = Exception("Connection failed")
            
            with pytest.raises(ConnectionError, match="Failed to connect to Anthropic API"):
                await provider.connect()
            
            assert provider.is_connected is False
    
    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnection."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.ANTHROPIC,
            api_key="test-key"
        )
        
        provider = AnthropicProvider(config)
        provider._client = Mock()  # Mock client
        provider._connected = True
        
        await provider.disconnect()
        
        assert provider.is_connected is False
        assert provider._client is None
    
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generation."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.ANTHROPIC,
            api_key="test-key",
            model="claude-3-5-sonnet-latest"
        )
        
        provider = AnthropicProvider(config)
        
        # Mock the response
        mock_response = Mock()
        mock_response.content = [Mock(text="Generated response")]
        mock_response.usage = Mock(input_tokens=20, output_tokens=10)
        mock_response.id = "response-id"
        mock_response.stop_reason = "end_turn"
        
        # Mock the client
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response
        provider._client = mock_client
        provider._connected = True
        
        # Create request
        request_config = LLMRequestConfig()
        request = LLMRequest(
            prompt="Test prompt",
            request_type=LLMRequestType.GENERATION,
            config=request_config
        )
        
        # Generate response
        response = await provider.generate(request)
        
        assert response.is_success is True
        assert response.content == "Generated response"
        assert response.tokens_used == 30  # 20 + 10
        assert response.cost > 0
        assert response.metadata.provider == "anthropic"
        assert response.metadata.model == "claude-3-5-sonnet-latest"
    
    @pytest.mark.asyncio
    async def test_generate_not_connected(self):
        """Test generation when not connected."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.ANTHROPIC,
            api_key="test-key"
        )
        
        provider = AnthropicProvider(config)
        provider._connected = False
        
        request_config = LLMRequestConfig()
        request = LLMRequest(
            prompt="Test prompt",
            request_type=LLMRequestType.GENERATION,
            config=request_config
        )
        
        with pytest.raises(ConnectionError, match="Provider not connected"):
            await provider.generate(request)
    
    @pytest.mark.asyncio
    async def test_health_check_connected(self):
        """Test health check when connected."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.ANTHROPIC,
            api_key="test-key"
        )
        
        provider = AnthropicProvider(config)
        
        # Mock successful health check
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Hello")]
        mock_response.usage = Mock(input_tokens=5, output_tokens=2)
        mock_response.id = "health-check-id"
        
        mock_client.messages.create.return_value = mock_response
        provider._client = mock_client
        provider._connected = True
        
        with patch.object(provider, '_test_connection', return_value=None):
            result = await provider.health_check()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_not_connected(self):
        """Test health check when not connected."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.ANTHROPIC,
            api_key="test-key"
        )
        
        provider = AnthropicProvider(config)
        provider._connected = False
        
        result = await provider.health_check()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager functionality."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.ANTHROPIC,
            api_key="test-key"
        )
        
        # Mock the connection
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Hello")]
        mock_response.usage = Mock(input_tokens=5, output_tokens=2)
        mock_response.id = "test-id"
        
        mock_client.messages.create.return_value = mock_response
        
        with patch('src.core.llm.providers.anthropic.AsyncAnthropic', return_value=mock_client):
            async with AnthropicProvider(config) as provider:
                assert provider.is_connected is True
            
            # Provider should be disconnected after context exit
            assert provider.is_connected is False
