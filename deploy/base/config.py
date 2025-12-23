"""
Base deployment configuration classes.

Provides common configuration structures and validation for all deployment providers.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DeploymentProvider(str, Enum):
    """Supported deployment providers."""

    GCP = "gcp"
    AWS = "aws"
    AZURE = "azure"
    DIGITALOCEAN = "digitalocean"
    LOCAL = "local"


class DeploymentConfigError(Exception):
    """Raised when deployment configuration is invalid."""

    pass


@dataclass
class ServiceConfig:
    """Common service configuration shared across all providers."""

    name: str
    image: str
    port: int = 8080
    memory: str = "4Gi"  # Updated: Required for NLP matching operations
    cpu: int = 2
    min_instances: int = 1
    max_instances: int = 100
    timeout: int = 300  # 5 minutes for long-running matching operations
    environment_vars: Dict[str, str] = field(default_factory=dict)
    secrets: Dict[str, str] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate service configuration."""
        if not self.name:
            raise DeploymentConfigError("Service name is required")
        if not self.image:
            raise DeploymentConfigError("Service image is required")
        if self.port < 1 or self.port > 65535:
            raise DeploymentConfigError(f"Invalid port: {self.port}")
        if self.cpu < 1:
            raise DeploymentConfigError(f"CPU must be at least 1, got {self.cpu}")
        if self.min_instances < 0:
            raise DeploymentConfigError(
                f"min_instances must be >= 0, got {self.min_instances}"
            )
        if self.max_instances < self.min_instances:
            raise DeploymentConfigError(
                f"max_instances ({self.max_instances}) must be >= min_instances ({self.min_instances})"
            )
        if self.timeout < 1:
            raise DeploymentConfigError(
                f"Timeout must be at least 1 second, got {self.timeout}"
            )


@dataclass
class BaseDeploymentConfig:
    """Base deployment configuration for all providers."""

    provider: DeploymentProvider
    environment: str = "production"
    region: Optional[str] = None  # Provider-specific format, no default
    service: ServiceConfig = field(
        default_factory=lambda: ServiceConfig(
            name="supply-graph-ai",
            image="ghcr.io/helpfulengineering/supply-graph-ai:latest",
        )
    )
    provider_config: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate deployment configuration."""
        if not self.provider:
            raise DeploymentConfigError("Provider is required")
        # Region validation is provider-specific, so we don't validate format here
        # Provider-specific deployers should validate region format
        if not self.environment:
            raise DeploymentConfigError("Environment is required")
        self.service.validate()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseDeploymentConfig":
        """Create configuration from dictionary."""
        provider_str = data.get("provider", "gcp")
        try:
            provider = DeploymentProvider(provider_str.lower())
        except ValueError:
            raise DeploymentConfigError(f"Unsupported provider: {provider_str}")

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

        # Region should be provided in config or set by provider-specific config
        # No default region to avoid provider-specific assumptions
        config = cls(
            provider=provider,
            environment=data.get("environment", "production"),
            region=data.get("region"),  # No default - must be specified
            service=service,
            provider_config=data.get("providers", {}).get(provider_str, {}),
        )

        config.validate()
        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "provider": self.provider.value,
            "environment": self.environment,
            "region": self.region,
            "service": {
                "name": self.service.name,
                "image": self.service.image,
                "port": self.service.port,
                "memory": self.service.memory,
                "cpu": self.service.cpu,
                "min_instances": self.service.min_instances,
                "max_instances": self.service.max_instances,
                "timeout": self.service.timeout,
                "environment_vars": self.service.environment_vars,
                "secrets": self.service.secrets,
                "labels": self.service.labels,
            },
            "providers": {
                self.provider.value: self.provider_config,
            },
        }
