"""
Configuration module for the Open Matching Engine

This module provides configuration management for all aspects
of the OME system, including LLM providers, storage, domains, and validation.
"""

from .domains import (
    DOMAIN_CONFIGS,
    DOMAIN_KEYWORDS,
    TYPE_DOMAIN_MAPPING,
    DomainConfig,
    DomainStatus,
    get_active_domains,
    get_all_domain_configs,
    get_domain_config,
    get_domain_keywords,
    infer_domain_from_type,
)
from .llm_config import (
    CredentialManager,
    LLMConfig,
    LLMConfigManager,
    LLMModelConfig,
    LLMProvider,
    LLMProviderConfig,
    LLMStatus,
    get_available_models,
    get_available_providers,
    get_llm_config,
    get_llm_config_manager,
    is_llm_enabled,
    validate_llm_config,
)
from .settings import (
    API_HOST,
    API_KEYS,
    API_PORT,
    CORS_ORIGINS,
    DEBUG,
    LLM_CONFIG,
    LLM_ENABLED,
    LOG_FILE,
    LOG_LEVEL,
    STORAGE_CONFIG,
)
from .storage_config import StorageConfigError, get_default_storage_config
from .validation import validate_configuration

__all__ = [
    # Main settings
    "DEBUG",
    "API_HOST",
    "API_PORT",
    "CORS_ORIGINS",
    "API_KEYS",
    "STORAGE_CONFIG",
    "LLM_CONFIG",
    "LLM_ENABLED",
    "LOG_LEVEL",
    "LOG_FILE",
    # LLM configuration
    "LLMProvider",
    "LLMStatus",
    "LLMModelConfig",
    "LLMProviderConfig",
    "LLMConfig",
    "CredentialManager",
    "LLMConfigManager",
    "get_llm_config_manager",
    "get_llm_config",
    "is_llm_enabled",
    "get_available_providers",
    "get_available_models",
    "validate_llm_config",
    # Domain configuration
    "DomainStatus",
    "DomainConfig",
    "DOMAIN_CONFIGS",
    "TYPE_DOMAIN_MAPPING",
    "DOMAIN_KEYWORDS",
    "get_domain_config",
    "get_all_domain_configs",
    "get_active_domains",
    "infer_domain_from_type",
    "get_domain_keywords",
    # Storage configuration
    "get_default_storage_config",
    "StorageConfigError",
    # Validation
    "validate_configuration",
]
