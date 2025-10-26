"""
Unit tests for the base LLM provider interface.

This module tests the base provider interface and data models to ensure
they work correctly before implementing specific providers.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from src.core.llm.providers.base import BaseLLMProvider, LLMProviderConfig, LLMProviderType
from src.core.llm.models.requests import LLMRequest, LLMRequestConfig, LLMRequestType
from src.core.llm.models.responses import LLMResponse, LLMResponseStatus, LLMResponseMetadata


class TestLLMProviderConfig:
    """Test LLM provider configuration."""
    
    def test_valid_config(self):
        """Test valid configuration creation."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.OPENAI,
            api_key="test-key",
            model="gpt-3.5-turbo",
            max_tokens=1000,
            temperature=0.5
        )
        
        assert config.provider_type == LLMProviderType.OPENAI
        assert config.api_key == "test-key"
        assert config.model == "gpt-3.5-turbo"
        assert config.max_tokens == 1000
        assert config.temperature == 0.5
    
    def test_invalid_max_tokens(self):
        """Test invalid max_tokens validation."""
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            LLMProviderConfig(
                provider_type=LLMProviderType.OPENAI,
                max_tokens=0
            )
    
    def test_invalid_temperature(self):
        """Test invalid temperature validation."""
        with pytest.raises(ValueError, match="temperature must be between 0.0 and 2.0"):
            LLMProviderConfig(
                provider_type=LLMProviderType.OPENAI,
                temperature=3.0
            )


class TestLLMRequest:
    """Test LLM request models."""
    
    def test_valid_request(self):
        """Test valid request creation."""
        config = LLMRequestConfig(max_tokens=1000, temperature=0.5)
        request = LLMRequest(
            prompt="Test prompt",
            request_type=LLMRequestType.GENERATION,
            config=config
        )
        
        assert request.prompt == "Test prompt"
        assert request.request_type == LLMRequestType.GENERATION
        assert request.config.max_tokens == 1000
        assert request.config.temperature == 0.5
    
    def test_empty_prompt_validation(self):
        """Test empty prompt validation."""
        config = LLMRequestConfig()
        
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            LLMRequest(
                prompt="",
                request_type=LLMRequestType.GENERATION,
                config=config
            )
    
    def test_whitespace_prompt_validation(self):
        """Test whitespace-only prompt validation."""
        config = LLMRequestConfig()
        
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            LLMRequest(
                prompt="   ",
                request_type=LLMRequestType.GENERATION,
                config=config
            )


class TestLLMResponse:
    """Test LLM response models."""
    
    def test_successful_response(self):
        """Test successful response creation."""
        metadata = LLMResponseMetadata(
            provider="openai",
            model="gpt-3.5-turbo",
            tokens_used=100,
            cost=0.01,
            processing_time=1.5
        )
        
        response = LLMResponse(
            content="Test response",
            status=LLMResponseStatus.SUCCESS,
            metadata=metadata
        )
        
        assert response.content == "Test response"
        assert response.status == LLMResponseStatus.SUCCESS
        assert response.is_success is True
        assert response.tokens_used == 100
        assert response.cost == 0.01
    
    def test_error_response(self):
        """Test error response creation."""
        metadata = LLMResponseMetadata(
            provider="openai",
            model="gpt-3.5-turbo",
            tokens_used=0,
            cost=0.0,
            processing_time=0.1
        )
        
        response = LLMResponse(
            content="",
            status=LLMResponseStatus.ERROR,
            metadata=metadata,
            error_message="Test error"
        )
        
        assert response.status == LLMResponseStatus.ERROR
        assert response.is_success is False
        assert response.error_message == "Test error"


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for testing."""
    
    async def connect(self) -> None:
        """Mock connect method."""
        self._connected = True
    
    async def disconnect(self) -> None:
        """Mock disconnect method."""
        self._connected = False
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Mock generate method."""
        metadata = LLMResponseMetadata(
            provider=self.provider_type.value,
            model=self.model,
            tokens_used=100,
            cost=0.01,
            processing_time=1.0
        )
        
        return LLMResponse(
            content="Mock response",
            status=LLMResponseStatus.SUCCESS,
            metadata=metadata
        )
    
    async def health_check(self) -> bool:
        """Mock health check method."""
        return self._connected
    
    def get_available_models(self) -> list[str]:
        """Mock get available models method."""
        return ["mock-model-1", "mock-model-2"]
    
    def estimate_cost(self, request: LLMRequest) -> float:
        """Mock estimate cost method."""
        return 0.01


class TestBaseLLMProvider:
    """Test base LLM provider interface."""
    
    def test_provider_initialization(self):
        """Test provider initialization."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.OPENAI,
            api_key="test-key"
        )
        
        provider = MockLLMProvider(config)
        
        assert provider.provider_type == LLMProviderType.OPENAI
        assert provider.model == "gpt-3.5-turbo"  # default
        assert provider.is_connected is False
    
    def test_missing_api_key_validation(self):
        """Test missing API key validation."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.OPENAI,
            api_key=None
        )
        
        with pytest.raises(ValueError, match="API key required"):
            MockLLMProvider(config)
    
    def test_local_provider_no_api_key(self):
        """Test local provider doesn't require API key."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.LOCAL,
            api_key=None
        )
        
        provider = MockLLMProvider(config)
        assert provider.provider_type == LLMProviderType.LOCAL
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager functionality."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.OPENAI,
            api_key="test-key"
        )
        
        async with MockLLMProvider(config) as provider:
            assert provider.is_connected is True
        
        # Provider should be disconnected after context exit
        assert provider.is_connected is False
    
    @pytest.mark.asyncio
    async def test_generate_request(self):
        """Test generating a request."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.OPENAI,
            api_key="test-key"
        )
        
        provider = MockLLMProvider(config)
        await provider.connect()
        
        request_config = LLMRequestConfig()
        request = LLMRequest(
            prompt="Test prompt",
            request_type=LLMRequestType.GENERATION,
            config=request_config
        )
        
        response = await provider.generate(request)
        
        assert response.is_success is True
        assert response.content == "Mock response"
        assert response.tokens_used == 100
        
        await provider.disconnect()
    
    def test_available_models(self):
        """Test getting available models."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.OPENAI,
            api_key="test-key"
        )
        
        provider = MockLLMProvider(config)
        models = provider.get_available_models()
        
        assert models == ["mock-model-1", "mock-model-2"]
    
    def test_estimate_cost(self):
        """Test cost estimation."""
        config = LLMProviderConfig(
            provider_type=LLMProviderType.OPENAI,
            api_key="test-key"
        )
        
        provider = MockLLMProvider(config)
        
        request_config = LLMRequestConfig()
        request = LLMRequest(
            prompt="Test prompt",
            request_type=LLMRequestType.GENERATION,
            config=request_config
        )
        
        cost = provider.estimate_cost(request)
        assert cost == 0.01
