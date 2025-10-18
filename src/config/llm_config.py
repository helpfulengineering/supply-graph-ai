"""
LLM Configuration for the Open Matching Engine

This module provides comprehensive configuration management for LLM providers,
including authentication, model selection, and provider-specific settings.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    AWS_BEDROCK = "aws_bedrock"
    LOCAL = "local"
    CUSTOM = "custom"


class LLMStatus(Enum):
    """Status of LLM configuration"""
    CONFIGURED = "configured"
    NOT_CONFIGURED = "not_configured"
    INVALID = "invalid"
    DISABLED = "disabled"


@dataclass
class LLMModelConfig:
    """Configuration for a specific LLM model"""
    name: str
    provider: LLMProvider
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout_seconds: int = 30
    retry_attempts: int = 3
    cost_per_token: Optional[float] = None
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "provider": self.provider.value,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "timeout_seconds": self.timeout_seconds,
            "retry_attempts": self.retry_attempts,
            "cost_per_token": self.cost_per_token,
            "description": self.description
        }


@dataclass
class LLMProviderConfig:
    """Configuration for an LLM provider"""
    provider: LLMProvider
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    organization_id: Optional[str] = None
    project_id: Optional[str] = None
    region: Optional[str] = None
    version: Optional[str] = None
    timeout_seconds: int = 30
    max_retries: int = 3
    rate_limit_requests_per_minute: int = 60
    rate_limit_tokens_per_minute: int = 150000
    custom_headers: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding sensitive data)"""
        return {
            "provider": self.provider.value,
            "api_base_url": self.api_base_url,
            "organization_id": self.organization_id,
            "project_id": self.project_id,
            "region": self.region,
            "version": self.version,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "rate_limit_requests_per_minute": self.rate_limit_requests_per_minute,
            "rate_limit_tokens_per_minute": self.rate_limit_tokens_per_minute,
            "custom_headers": self.custom_headers,
            "enabled": self.enabled,
            "has_api_key": self.api_key is not None
        }


@dataclass
class LLMConfig:
    """Main LLM configuration"""
    enabled: bool = False
    default_provider: Optional[LLMProvider] = None
    default_model: Optional[str] = None
    fallback_enabled: bool = True
    cost_tracking_enabled: bool = True
    usage_analytics_enabled: bool = True
    prompt_caching_enabled: bool = True
    response_caching_enabled: bool = False
    cache_ttl_seconds: int = 3600
    max_concurrent_requests: int = 10
    request_timeout_seconds: int = 60
    providers: Dict[LLMProvider, LLMProviderConfig] = field(default_factory=dict)
    models: Dict[str, LLMModelConfig] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding sensitive data)"""
        return {
            "enabled": self.enabled,
            "default_provider": self.default_provider.value if self.default_provider else None,
            "default_model": self.default_model,
            "fallback_enabled": self.fallback_enabled,
            "cost_tracking_enabled": self.cost_tracking_enabled,
            "usage_analytics_enabled": self.usage_analytics_enabled,
            "prompt_caching_enabled": self.prompt_caching_enabled,
            "response_caching_enabled": self.response_caching_enabled,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "max_concurrent_requests": self.max_concurrent_requests,
            "request_timeout_seconds": self.request_timeout_seconds,
            "providers": {p.value: config.to_dict() for p, config in self.providers.items()},
            "models": {name: model.to_dict() for name, model in self.models.items()}
        }


class CredentialManager:
    """Secure credential management for LLM providers"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize credential manager.
        
        Args:
            encryption_key: Optional encryption key. If not provided, will use environment variable
                          or generate a new one (not recommended for production)
        """
        self.encryption_key = encryption_key or os.getenv("LLM_ENCRYPTION_KEY")
        self._fernet = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption for credential storage"""
        if self.encryption_key:
            # Use provided key
            key = self.encryption_key.encode()
        else:
            # Generate key from environment or create new one
            salt = os.getenv("LLM_ENCRYPTION_SALT", "default_salt").encode()
            password = os.getenv("LLM_ENCRYPTION_PASSWORD", "default_password").encode()
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
        
        self._fernet = Fernet(key)
    
    def encrypt_credential(self, credential: str) -> str:
        """Encrypt a credential"""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        return self._fernet.encrypt(credential.encode()).decode()
    
    def decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt a credential"""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        return self._fernet.decrypt(encrypted_credential.encode()).decode()
    
    def store_credential(self, provider: LLMProvider, credential_type: str, credential: str) -> str:
        """Store an encrypted credential"""
        encrypted = self.encrypt_credential(credential)
        # In a real implementation, this would store to a secure credential store
        # For now, we'll just return the encrypted value
        logger.info(f"Stored encrypted credential for {provider.value}:{credential_type}")
        return encrypted
    
    def retrieve_credential(self, provider: LLMProvider, credential_type: str) -> Optional[str]:
        """Retrieve and decrypt a credential"""
        # In a real implementation, this would retrieve from a secure credential store
        # For now, we'll return None to indicate no stored credential
        logger.debug(f"Retrieving credential for {provider.value}:{credential_type}")
        return None


class LLMConfigManager:
    """Manager for LLM configuration"""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize LLM configuration manager.
        
        Args:
            config_file: Optional path to configuration file
        """
        self.config_file = config_file or Path("config/llm_config.json")
        self.credential_manager = CredentialManager()
        self.config = LLMConfig()
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file and environment"""
        # Load from file if it exists
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                self._load_from_dict(config_data)
                logger.info(f"Loaded LLM configuration from {self.config_file}")
            except Exception as e:
                logger.warning(f"Failed to load LLM config from file: {e}")
        
        # Override with environment variables
        self._load_from_environment()
    
    def _load_from_dict(self, config_data: Dict[str, Any]):
        """Load configuration from dictionary"""
        self.config.enabled = config_data.get("enabled", False)
        self.config.default_provider = LLMProvider(config_data["default_provider"]) if config_data.get("default_provider") else None
        self.config.default_model = config_data.get("default_model")
        self.config.fallback_enabled = config_data.get("fallback_enabled", True)
        self.config.cost_tracking_enabled = config_data.get("cost_tracking_enabled", True)
        self.config.usage_analytics_enabled = config_data.get("usage_analytics_enabled", True)
        self.config.prompt_caching_enabled = config_data.get("prompt_caching_enabled", True)
        self.config.response_caching_enabled = config_data.get("response_caching_enabled", False)
        self.config.cache_ttl_seconds = config_data.get("cache_ttl_seconds", 3600)
        self.config.max_concurrent_requests = config_data.get("max_concurrent_requests", 10)
        self.config.request_timeout_seconds = config_data.get("request_timeout_seconds", 60)
        
        # Load providers
        for provider_name, provider_data in config_data.get("providers", {}).items():
            provider = LLMProvider(provider_name)
            self.config.providers[provider] = LLMProviderConfig(
                provider=provider,
                api_base_url=provider_data.get("api_base_url"),
                organization_id=provider_data.get("organization_id"),
                project_id=provider_data.get("project_id"),
                region=provider_data.get("region"),
                version=provider_data.get("version"),
                timeout_seconds=provider_data.get("timeout_seconds", 30),
                max_retries=provider_data.get("max_retries", 3),
                rate_limit_requests_per_minute=provider_data.get("rate_limit_requests_per_minute", 60),
                rate_limit_tokens_per_minute=provider_data.get("rate_limit_tokens_per_minute", 150000),
                custom_headers=provider_data.get("custom_headers", {}),
                enabled=provider_data.get("enabled", True)
            )
        
        # Load models
        for model_name, model_data in config_data.get("models", {}).items():
            self.config.models[model_name] = LLMModelConfig(
                name=model_name,
                provider=LLMProvider(model_data["provider"]),
                max_tokens=model_data.get("max_tokens", 4096),
                temperature=model_data.get("temperature", 0.7),
                top_p=model_data.get("top_p", 1.0),
                frequency_penalty=model_data.get("frequency_penalty", 0.0),
                presence_penalty=model_data.get("presence_penalty", 0.0),
                timeout_seconds=model_data.get("timeout_seconds", 30),
                retry_attempts=model_data.get("retry_attempts", 3),
                cost_per_token=model_data.get("cost_per_token"),
                description=model_data.get("description")
            )
    
    def _load_from_environment(self):
        """Load configuration from environment variables"""
        # Global LLM settings
        if os.getenv("LLM_ENABLED"):
            self.config.enabled = os.getenv("LLM_ENABLED").lower() in ("true", "1", "t")
        
        if os.getenv("LLM_DEFAULT_PROVIDER"):
            try:
                self.config.default_provider = LLMProvider(os.getenv("LLM_DEFAULT_PROVIDER"))
            except ValueError:
                logger.warning(f"Invalid LLM provider: {os.getenv('LLM_DEFAULT_PROVIDER')}")
        
        if os.getenv("LLM_DEFAULT_MODEL"):
            self.config.default_model = os.getenv("LLM_DEFAULT_MODEL")
        
        # Provider-specific settings
        for provider in LLMProvider:
            provider_name = provider.value.upper()
            
            # API Key
            api_key = os.getenv(f"{provider_name}_API_KEY")
            if api_key:
                if provider not in self.config.providers:
                    self.config.providers[provider] = LLMProviderConfig(provider=provider)
                self.config.providers[provider].api_key = api_key
            
            # Base URL
            api_base_url = os.getenv(f"{provider_name}_API_BASE_URL")
            if api_base_url:
                if provider not in self.config.providers:
                    self.config.providers[provider] = LLMProviderConfig(provider=provider)
                self.config.providers[provider].api_base_url = api_base_url
            
            # Organization ID (for OpenAI)
            if provider == LLMProvider.OPENAI:
                org_id = os.getenv("OPENAI_ORGANIZATION_ID")
                if org_id:
                    if provider not in self.config.providers:
                        self.config.providers[provider] = LLMProviderConfig(provider=provider)
                    self.config.providers[provider].organization_id = org_id
    
    def get_provider_config(self, provider: LLMProvider) -> Optional[LLMProviderConfig]:
        """Get configuration for a specific provider"""
        return self.config.providers.get(provider)
    
    def get_model_config(self, model_name: str) -> Optional[LLMModelConfig]:
        """Get configuration for a specific model"""
        return self.config.models.get(model_name)
    
    def is_provider_configured(self, provider: LLMProvider) -> bool:
        """Check if a provider is properly configured"""
        provider_config = self.get_provider_config(provider)
        if not provider_config or not provider_config.enabled:
            return False
        
        # Check if API key is available
        if provider_config.api_key:
            return True
        
        # Check environment variables as fallback
        provider_name = provider.value.upper()
        return os.getenv(f"{provider_name}_API_KEY") is not None
    
    def get_available_providers(self) -> List[LLMProvider]:
        """Get list of available (configured) providers"""
        return [provider for provider in LLMProvider if self.is_provider_configured(provider)]
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        available_models = []
        for model_name, model_config in self.config.models.items():
            if self.is_provider_configured(model_config.provider):
                available_models.append(model_name)
        return available_models
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate the current configuration"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "providers": {},
            "models": {}
        }
        
        # Check if LLM is enabled
        if not self.config.enabled:
            validation_result["warnings"].append("LLM integration is disabled")
        
        # Validate providers
        for provider in LLMProvider:
            provider_config = self.get_provider_config(provider)
            provider_status = {
                "configured": self.is_provider_configured(provider),
                "enabled": provider_config.enabled if provider_config else False,
                "has_api_key": bool(provider_config.api_key if provider_config else False),
                "errors": []
            }
            
            if provider_config and provider_config.enabled:
                if not provider_config.api_key and not os.getenv(f"{provider.value.upper()}_API_KEY"):
                    provider_status["errors"].append("No API key configured")
                    validation_result["errors"].append(f"{provider.value}: No API key configured")
            
            validation_result["providers"][provider.value] = provider_status
        
        # Validate models
        for model_name, model_config in self.config.models.items():
            model_status = {
                "configured": True,
                "provider_available": self.is_provider_configured(model_config.provider),
                "errors": []
            }
            
            if not model_status["provider_available"]:
                model_status["errors"].append(f"Provider {model_config.provider.value} not configured")
                validation_result["errors"].append(f"Model {model_name}: Provider not configured")
            
            validation_result["models"][model_name] = model_status
        
        # Overall validation
        if validation_result["errors"]:
            validation_result["valid"] = False
        
        return validation_result
    
    def save_config(self):
        """Save configuration to file"""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save configuration (excluding sensitive data)
            with open(self.config_file, 'w') as f:
                json.dump(self.config.to_dict(), f, indent=2)
            
            logger.info(f"Saved LLM configuration to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save LLM configuration: {e}")
            raise


# Global configuration manager instance
_config_manager: Optional[LLMConfigManager] = None


def get_llm_config_manager() -> LLMConfigManager:
    """Get the global LLM configuration manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = LLMConfigManager()
    return _config_manager


def get_llm_config() -> LLMConfig:
    """Get the current LLM configuration"""
    return get_llm_config_manager().config


def is_llm_enabled() -> bool:
    """Check if LLM integration is enabled"""
    return get_llm_config().enabled


def get_available_providers() -> List[LLMProvider]:
    """Get list of available LLM providers"""
    return get_llm_config_manager().get_available_providers()


def get_available_models() -> List[str]:
    """Get list of available LLM models"""
    return get_llm_config_manager().get_available_models()


def validate_llm_config() -> Dict[str, Any]:
    """Validate the LLM configuration"""
    return get_llm_config_manager().validate_config()
