"""
Configuration module for the Open Matching Engine

This module provides configuration management for all aspects
of the OME system, including LLM providers, storage, domains, and validation.
"""

from .settings import (
    DEBUG,
    API_HOST,
    API_PORT,
    CORS_ORIGINS,
    API_KEYS,
    STORAGE_CONFIG,
    LLM_CONFIG,
    LLM_ENABLED,
    LOG_LEVEL,
    LOG_FILE
)

from .llm_config import (
    LLMProvider,
    LLMStatus,
    LLMModelConfig,
    LLMProviderConfig,
    LLMConfig,
    CredentialManager,
    LLMConfigManager,
    get_llm_config_manager,
    get_llm_config,
    is_llm_enabled,
    get_available_providers,
    get_available_models,
    validate_llm_config
)

from .domains import (
    DomainStatus,
    DomainConfig,
    DOMAIN_CONFIGS,
    TYPE_DOMAIN_MAPPING,
    DOMAIN_KEYWORDS,
    get_domain_config,
    get_all_domain_configs,
    get_active_domains,
    infer_domain_from_type,
    get_domain_keywords
)

from .storage_config import (
    get_default_storage_config,
    StorageConfigError
)

from .validation import (
    validate_configuration
)

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
    "validate_configuration"
]
