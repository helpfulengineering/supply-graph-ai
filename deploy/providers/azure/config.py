"""
Azure-specific deployment configuration.

Extends BaseDeploymentConfig with Azure-specific defaults and validation.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional

from ...base.config import (
    BaseDeploymentConfig,
    DeploymentProvider,
    ServiceConfig,
    DeploymentConfigError,
)


@dataclass
class AzureDeploymentConfig(BaseDeploymentConfig):
    """Azure-specific deployment configuration with Azure defaults."""

    def __post_init__(self):
        """Set Azure-specific defaults after initialization."""
        # Set provider if not already set
        if self.provider != DeploymentProvider.AZURE:
            raise DeploymentConfigError(
                f"AzureDeploymentConfig requires provider=AZURE, got {self.provider}"
            )

        # Set Azure-specific default region if not provided
        if self.region is None:
            self.region = "eastus"  # Azure format: eastus

        # Validate Azure region format (e.g., eastus, westus, westeurope)
        if self.region and not self._is_valid_azure_region(self.region):
            raise DeploymentConfigError(
                f"Invalid Azure region format: {self.region}. "
                "Azure regions use format like 'eastus', 'westus', 'westeurope'"
            )

        # Validate Azure-specific config
        self._validate_azure_config()

    def _is_valid_azure_region(self, region: str) -> bool:
        """
        Validate Azure region format.

        Azure regions use format: {direction}{location}
        Examples: eastus, westus, westeurope, southeastasia
        
        Note: This is a basic format check. For production, you might want
        to validate against a list of actual Azure regions.
        """
        if not region:
            return False

        # Azure regions are typically lowercase, no dashes, no numbers at the end
        # Examples: eastus, westus, westeurope, southeastasia
        # They don't have dashes like AWS or numbers like GCP
        if "-" in region:
            # Azure regions don't use dashes (unlike AWS: us-east-1)
            return False

        if region[-1].isdigit():
            # Azure regions don't end with numbers (unlike GCP: us-west1)
            return False

        # Basic check: should be alphanumeric, lowercase
        if not region.isalnum() or not region.islower():
            return False

        return True

    def _validate_azure_config(self) -> None:
        """Validate Azure-specific configuration."""
        # Check for required Azure config
        if "resource_group" not in self.provider_config:
            raise DeploymentConfigError(
                "Azure deployment requires 'resource_group' in provider_config"
            )

        if "subscription_id" not in self.provider_config:
            raise DeploymentConfigError(
                "Azure deployment requires 'subscription_id' in provider_config"
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AzureDeploymentConfig":
        """Create Azure configuration from dictionary."""
        # Ensure provider is Azure
        provider_str = data.get("provider", "azure").lower()
        if provider_str != "azure":
            raise DeploymentConfigError(
                f"AzureDeploymentConfig requires provider=azure, got {provider_str}"
            )

        # Parse service config
        service_data = data.get("service", {})
        service = ServiceConfig(
            name=service_data.get("name", "supply-graph-ai"),
            image=service_data.get("image", "ghcr.io/helpfulengineering/supply-graph-ai:latest"),
            port=service_data.get("port", 8080),
            memory=service_data.get("memory", "4Gi"),
            cpu=service_data.get("cpu", 2),
            min_instances=service_data.get("min_instances", 1),
            max_instances=service_data.get("max_instances", 100),
            timeout=service_data.get("timeout", 300),
            environment_vars=service_data.get("environment_vars", {}),
            secrets=service_data.get("secrets", {}),
            labels=service_data.get("labels", {}),
        )

        # Get Azure-specific config
        azure_config = data.get("providers", {}).get("azure", {})

        config = cls(
            provider=DeploymentProvider.AZURE,
            environment=data.get("environment", "production"),
            region=data.get("region"),  # Will default to eastus in __post_init__
            service=service,
            provider_config=azure_config,
        )

        return config

    @classmethod
    def with_defaults(
        cls,
        resource_group: str,
        subscription_id: str,
        region: Optional[str] = None,
        service_name: str = "supply-graph-ai",
        **kwargs
    ) -> "AzureDeploymentConfig":
        """
        Create Azure config with sensible defaults.

        Args:
            resource_group: Azure resource group name (required)
            subscription_id: Azure subscription ID (required)
            region: Azure region (defaults to eastus)
            service_name: Service name (defaults to supply-graph-ai)
            **kwargs: Additional configuration overrides

        Returns:
            AzureDeploymentConfig instance
        """
        # Extract service config kwargs
        service_kwargs = {
            "name": service_name,
            "image": kwargs.pop("image", "ghcr.io/helpfulengineering/supply-graph-ai:latest"),
            "port": kwargs.pop("port", 8080),
            "memory": kwargs.pop("memory", "4Gi"),
            "cpu": kwargs.pop("cpu", 2),
            "min_instances": kwargs.pop("min_instances", 1),
            "max_instances": kwargs.pop("max_instances", 100),
            "timeout": kwargs.pop("timeout", 300),
            "environment_vars": kwargs.pop("environment_vars", {}),
            "secrets": kwargs.pop("secrets", {}),
            "labels": kwargs.pop("labels", {}),
        }

        # Build provider config
        provider_config = {
            "resource_group": resource_group,
            "subscription_id": subscription_id,
            **kwargs.pop("provider_config", {}),
        }

        # Remaining kwargs go to top-level config
        config_kwargs = {
            "provider": DeploymentProvider.AZURE,
            "environment": kwargs.pop("environment", "production"),
            "region": region,  # Will default to eastus in __post_init__
            "service": ServiceConfig(**service_kwargs),
            "provider_config": provider_config,
        }

        # Any remaining kwargs are invalid
        if kwargs:
            raise DeploymentConfigError(
                f"Unexpected keyword arguments: {list(kwargs.keys())}. "
                "Use 'provider_config' for Azure-specific settings."
            )

        return cls(**config_kwargs)

