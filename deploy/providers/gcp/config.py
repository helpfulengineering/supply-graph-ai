"""
GCP-specific deployment configuration.

Extends BaseDeploymentConfig with GCP-specific defaults and validation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ...base.config import (
    BaseDeploymentConfig,
    DeploymentConfigError,
    DeploymentProvider,
    ServiceConfig,
)


@dataclass
class GCPDeploymentConfig(BaseDeploymentConfig):
    """GCP-specific deployment configuration with GCP defaults."""

    def __post_init__(self):
        """Set GCP-specific defaults after initialization."""
        # Set provider if not already set
        if self.provider != DeploymentProvider.GCP:
            raise DeploymentConfigError(
                f"GCPDeploymentConfig requires provider=GCP, got {self.provider}"
            )

        # Set GCP-specific default region if not provided
        if self.region is None:
            self.region = "us-west1"  # GCP format: us-west1

        # Validate GCP region format (e.g., us-west1, us-east1, europe-west1)
        if self.region and not self._is_valid_gcp_region(self.region):
            raise DeploymentConfigError(
                f"Invalid GCP region format: {self.region}. "
                "GCP regions use format like 'us-west1', 'us-east1', 'europe-west1'"
            )

        # Validate GCP-specific config
        self._validate_gcp_config()

    def _is_valid_gcp_region(self, region: str) -> bool:
        """
        Validate GCP region format.

        GCP regions use format: {location}-{number}
        Examples: us-west1, us-east1, europe-west1, asia-southeast1

        Note: This is a basic format check. For production, you might want
        to validate against a list of actual GCP regions.
        """
        if not region:
            return False

        # Basic format check: should have at least one dash
        parts = region.split("-")
        if len(parts) < 2:
            return False

        # Last part should be a number (region number like 1, 2, 3, etc.)
        # But it could also be a multi-part location like "southeast1"
        # So we check if the last part ends with a digit
        last_part = parts[-1]
        if not last_part:
            return False

        # Check if last part ends with a digit (e.g., "west1", "southeast1")
        if not last_part[-1].isdigit():
            return False

        # Check that it's not AWS format (us-west-1 has three parts with number as separate part)
        # GCP: us-west1 (2 parts, number at end of second part)
        # AWS: us-west-1 (3 parts, number is third part)
        if len(parts) == 3 and parts[-1].isdigit() and len(parts[-1]) == 1:
            # This looks like AWS format (e.g., us-west-1)
            return False

        return True

    def _validate_gcp_config(self) -> None:
        """Validate GCP-specific configuration."""
        # Check for required GCP config
        if "project_id" not in self.provider_config:
            raise DeploymentConfigError(
                "GCP deployment requires 'project_id' in provider_config"
            )

        # Validate project ID format (alphanumeric, hyphens, but not starting/ending with hyphen)
        project_id = self.provider_config.get("project_id", "")
        if not project_id:
            raise DeploymentConfigError("GCP project_id cannot be empty")

        # GCP project IDs: 6-30 characters, lowercase letters, numbers, hyphens
        # Cannot start or end with hyphen
        if not (6 <= len(project_id) <= 30):
            raise DeploymentConfigError(
                f"GCP project_id must be 6-30 characters, got {len(project_id)}"
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GCPDeploymentConfig":
        """Create GCP configuration from dictionary."""
        # Ensure provider is GCP
        provider_str = data.get("provider", "gcp").lower()
        if provider_str != "gcp":
            raise DeploymentConfigError(
                f"GCPDeploymentConfig requires provider=gcp, got {provider_str}"
            )

        # Parse service config
        service_data = data.get("service", {})
        service = ServiceConfig(
            name=service_data.get("name", "supply-graph-ai"),
            image=service_data.get(
                "image", "ghcr.io/helpfulengineering/supply-graph-ai:latest"
            ),
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

        # Get GCP-specific config
        gcp_config = data.get("providers", {}).get("gcp", {})

        config = cls(
            provider=DeploymentProvider.GCP,
            environment=data.get("environment", "production"),
            region=data.get("region"),  # Will default to us-west1 in __post_init__
            service=service,
            provider_config=gcp_config,
        )

        return config

    @classmethod
    def with_defaults(
        cls,
        project_id: str,
        region: Optional[str] = None,
        service_name: str = "supply-graph-ai",
        **kwargs,
    ) -> "GCPDeploymentConfig":
        """
        Create GCP config with sensible defaults.

        Args:
            project_id: GCP project ID (required)
            region: GCP region (defaults to us-west1)
            service_name: Service name (defaults to supply-graph-ai)
            **kwargs: Additional configuration overrides

        Returns:
            GCPDeploymentConfig instance
        """
        # Extract service config kwargs
        service_kwargs = {
            "name": service_name,
            "image": kwargs.pop(
                "image", "ghcr.io/helpfulengineering/supply-graph-ai:latest"
            ),
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
            "project_id": project_id,
            **kwargs.pop("provider_config", {}),
        }

        # Remaining kwargs go to top-level config
        config_kwargs = {
            "provider": DeploymentProvider.GCP,
            "environment": kwargs.pop("environment", "production"),
            "region": region,  # Will default to us-west1 in __post_init__
            "service": ServiceConfig(**service_kwargs),
            "provider_config": provider_config,
        }

        # Any remaining kwargs are invalid
        if kwargs:
            raise DeploymentConfigError(
                f"Unexpected keyword arguments: {list(kwargs.keys())}. "
                "Use 'provider_config' for GCP-specific settings."
            )

        return cls(**config_kwargs)
