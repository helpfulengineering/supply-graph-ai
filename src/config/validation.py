"""
Configuration validation for the Open Matching Engine

This module provides comprehensive validation for all configuration components,
ensuring that the system is properly configured before startup.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import json
import yaml

from .llm_config import validate_llm_config, get_llm_config_manager
from .storage_config import get_default_storage_config, StorageConfigError
from .domains import get_all_domain_configs, DomainStatus

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Exception raised for configuration errors"""
    pass


class ConfigurationWarning(Exception):
    """Exception raised for configuration warnings"""
    pass


@dataclass
class ValidationResult:
    """Result of configuration validation"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    details: Dict[str, Any]
    
    def add_error(self, error: str):
        """Add an error to the validation result"""
        self.errors.append(error)
        self.valid = False
    
    def add_warning(self, warning: str):
        """Add a warning to the validation result"""
        self.warnings.append(warning)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "details": self.details
        }


class ConfigurationValidator:
    """Comprehensive configuration validator"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_all(self) -> ValidationResult:
        """Validate all configuration components"""
        result = ValidationResult(valid=True, errors=[], warnings=[], details={})
        
        # Validate each component
        result.details["llm"] = self._validate_llm_config()
        result.details["storage"] = self._validate_storage_config()
        result.details["domains"] = self._validate_domain_config()
        result.details["environment"] = self._validate_environment()
        result.details["files"] = self._validate_config_files()
        
        # Aggregate results
        for component, component_result in result.details.items():
            if isinstance(component_result, dict):
                if not component_result.get("valid", True):
                    result.add_error(f"{component}: {component_result.get('error', 'Validation failed')}")
                if component_result.get("warnings"):
                    for warning in component_result["warnings"]:
                        result.add_warning(f"{component}: {warning}")
        
        return result
    
    def _validate_llm_config(self) -> Dict[str, Any]:
        """Validate LLM configuration"""
        try:
            llm_validation = validate_llm_config()
            return {
                "valid": llm_validation["valid"],
                "errors": llm_validation.get("errors", []),
                "warnings": llm_validation.get("warnings", []),
                "providers": llm_validation.get("providers", {}),
                "models": llm_validation.get("models", {})
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Failed to validate LLM configuration: {e}",
                "errors": [str(e)],
                "warnings": []
            }
    
    def _validate_storage_config(self) -> Dict[str, Any]:
        """Validate storage configuration"""
        try:
            storage_config = get_default_storage_config()
            return {
                "valid": True,
                "provider": storage_config.provider,
                "bucket_name": storage_config.bucket_name,
                "warnings": []
            }
        except StorageConfigError as e:
            return {
                "valid": False,
                "error": f"Storage configuration error: {e}",
                "errors": [str(e)],
                "warnings": []
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Failed to validate storage configuration: {e}",
                "errors": [str(e)],
                "warnings": []
            }
    
    def _validate_domain_config(self) -> Dict[str, Any]:
        """Validate domain configuration"""
        try:
            domain_configs = get_all_domain_configs()
            active_domains = [name for name, config in domain_configs.items() 
                            if config.status == DomainStatus.ACTIVE]
            
            warnings = []
            if not active_domains:
                warnings.append("No active domains configured")
            
            return {
                "valid": True,
                "total_domains": len(domain_configs),
                "active_domains": active_domains,
                "warnings": warnings
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Failed to validate domain configuration: {e}",
                "errors": [str(e)],
                "warnings": []
            }
    
    def _validate_environment(self) -> Dict[str, Any]:
        """Validate environment variables"""
        warnings = []
        errors = []
        
        # Check required environment variables
        required_vars = ["LOG_LEVEL"]
        for var in required_vars:
            if not os.getenv(var):
                warnings.append(f"Environment variable {var} not set, using default")
        
        # Check optional but recommended variables
        recommended_vars = ["LLM_ENABLED", "LLM_DEFAULT_PROVIDER"]
        for var in recommended_vars:
            if not os.getenv(var):
                warnings.append(f"Recommended environment variable {var} not set")
        
        # Check for conflicting variables
        if os.getenv("LLM_ENABLED") == "true" and not os.getenv("LLM_DEFAULT_PROVIDER"):
            warnings.append("LLM enabled but no default provider specified")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_config_files(self) -> Dict[str, Any]:
        """Validate configuration files"""
        warnings = []
        errors = []
        
        # Check for configuration files
        config_files = [
            "config/llm_config.json",
            ".env",
            "config/domains.yaml"
        ]
        
        existing_files = []
        for file_path in config_files:
            if Path(file_path).exists():
                existing_files.append(file_path)
            else:
                warnings.append(f"Configuration file {file_path} not found")
        
        # Validate JSON files
        for file_path in existing_files:
            if file_path.endswith('.json'):
                try:
                    with open(file_path, 'r') as f:
                        json.load(f)
                except json.JSONDecodeError as e:
                    errors.append(f"Invalid JSON in {file_path}: {e}")
                except Exception as e:
                    errors.append(f"Error reading {file_path}: {e}")
        
        # Validate YAML files
        for file_path in existing_files:
            if file_path.endswith(('.yaml', '.yml')):
                try:
                    with open(file_path, 'r') as f:
                        yaml.safe_load(f)
                except yaml.YAMLError as e:
                    errors.append(f"Invalid YAML in {file_path}: {e}")
                except Exception as e:
                    errors.append(f"Error reading {file_path}: {e}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "existing_files": existing_files
        }
    
    def validate_llm_provider(self, provider_name: str) -> Dict[str, Any]:
        """Validate configuration for a specific LLM provider"""
        try:
            from .llm_config import LLMProvider, get_llm_config_manager
            
            provider = LLMProvider(provider_name)
            config_manager = get_llm_config_manager()
            
            result = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "provider": provider_name
            }
            
            # Check if provider is configured
            if not config_manager.is_provider_configured(provider):
                result["valid"] = False
                result["errors"].append(f"Provider {provider_name} is not configured")
                return result
            
            # Get provider configuration
            provider_config = config_manager.get_provider_config(provider)
            if not provider_config:
                result["valid"] = False
                result["errors"].append(f"Provider configuration not found for {provider_name}")
                return result
            
            # Validate API key
            if not provider_config.api_key:
                env_var = f"{provider_name.upper()}_API_KEY"
                if not os.getenv(env_var):
                    result["valid"] = False
                    result["errors"].append(f"No API key configured for {provider_name}")
            
            # Validate base URL if provided
            if provider_config.api_base_url:
                if not provider_config.api_base_url.startswith(('http://', 'https://')):
                    result["warnings"].append(f"Invalid base URL format for {provider_name}")
            
            # Provider-specific validations
            if provider == LLMProvider.OPENAI:
                if not provider_config.organization_id and not os.getenv("OPENAI_ORGANIZATION_ID"):
                    result["warnings"].append("OpenAI organization ID not configured")
            
            elif provider == LLMProvider.AZURE_OPENAI:
                if not provider_config.region:
                    result["warnings"].append("Azure OpenAI region not configured")
                if not provider_config.version:
                    result["warnings"].append("Azure OpenAI API version not configured")
            
            return result
            
        except ValueError:
            return {
                "valid": False,
                "errors": [f"Unknown provider: {provider_name}"],
                "warnings": [],
                "provider": provider_name
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate provider {provider_name}: {e}"],
                "warnings": [],
                "provider": provider_name
            }


# Global validator instance
_validator: Optional[ConfigurationValidator] = None


def get_config_validator() -> ConfigurationValidator:
    """Get the global configuration validator"""
    global _validator
    if _validator is None:
        _validator = ConfigurationValidator()
    return _validator


def validate_configuration() -> ValidationResult:
    """Validate the entire configuration"""
    return get_config_validator().validate_all()


def validate_llm_provider(provider_name: str) -> Dict[str, Any]:
    """Validate configuration for a specific LLM provider"""
    return get_config_validator().validate_llm_provider(provider_name)


def check_configuration_health() -> Dict[str, Any]:
    """Check the overall health of the configuration"""
    validation_result = validate_configuration()
    
    health_status = {
        "healthy": validation_result.valid,
        "status": "healthy" if validation_result.valid else "unhealthy",
        "errors": validation_result.errors,
        "warnings": validation_result.warnings,
        "components": validation_result.details
    }
    
    # Determine overall status
    if validation_result.errors:
        health_status["status"] = "unhealthy"
    elif validation_result.warnings:
        health_status["status"] = "degraded"
    
    return health_status