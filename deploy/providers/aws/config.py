"""
AWS-specific deployment configuration.

Extends BaseDeploymentConfig with AWS-specific defaults and validation.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ...base.config import (
    BaseDeploymentConfig,
    DeploymentConfigError,
    DeploymentProvider,
    ServiceConfig,
)


@dataclass
class AWSDeploymentConfig(BaseDeploymentConfig):
    """AWS-specific deployment configuration with AWS defaults."""

    def __post_init__(self):
        """Set AWS-specific defaults after initialization."""
        # Set provider if not already set
        if self.provider != DeploymentProvider.AWS:
            raise DeploymentConfigError(
                f"AWSDeploymentConfig requires provider=AWS, got {self.provider}"
            )

        # Set AWS-specific default region if not provided
        if self.region is None:
            self.region = "us-east-1"  # AWS format: us-east-1

        # Validate AWS region format (e.g., us-east-1, us-west-2, eu-west-1)
        if self.region and not self._is_valid_aws_region(self.region):
            raise DeploymentConfigError(
                f"Invalid AWS region format: {self.region}. "
                "AWS regions use format like 'us-east-1', 'us-west-2', 'eu-west-1'"
            )

        # Validate AWS-specific config
        self._validate_aws_config()

    def _is_valid_aws_region(self, region: str) -> bool:
        """
        Validate AWS region format.

        AWS regions use format: {location}-{direction}-{number}
        Examples: us-east-1, us-west-2, eu-west-1, ap-southeast-1

        Note: This is a basic format check. For production, you might want
        to validate against a list of actual AWS regions.
        """
        if not region:
            return False

        # Basic format check: should have at least two dashes
        parts = region.split("-")
        if len(parts) < 3:
            return False

        # Last part should be a number (region number like 1, 2, 3, etc.)
        last_part = parts[-1]
        if not last_part or not last_part.isdigit():
            return False

        # Check that it's not GCP format (us-west1 has 2 parts with number at end of second part)
        # AWS: us-west-1 (3 parts, number is third part)
        # GCP: us-west1 (2 parts, number at end of second part)
        if len(parts) == 2 and parts[-1][-1].isdigit():
            # This looks like GCP format (e.g., us-west1)
            return False

        return True

    def _validate_aws_config(self) -> None:
        """Validate AWS-specific configuration."""
        # Check for required AWS config
        # AWS deployments typically need cluster, task definition, or ECR repository
        # But these can vary by deployment method (ECS, Fargate, EKS, etc.)
        # So we'll be lenient here and let the deployer validate specifics
        pass

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AWSDeploymentConfig":
        """Create AWS configuration from dictionary."""
        # Ensure provider is AWS
        provider_str = data.get("provider", "aws").lower()
        if provider_str != "aws":
            raise DeploymentConfigError(
                f"AWSDeploymentConfig requires provider=aws, got {provider_str}"
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

        # Get AWS-specific config
        aws_config = data.get("providers", {}).get("aws", {})

        config = cls(
            provider=DeploymentProvider.AWS,
            environment=data.get("environment", "production"),
            region=data.get("region"),  # Will default to us-east-1 in __post_init__
            service=service,
            provider_config=aws_config,
        )

        return config

    @classmethod
    def with_defaults(
        cls,
        region: Optional[str] = None,
        service_name: str = "supply-graph-ai",
        **kwargs,
    ) -> "AWSDeploymentConfig":
        """
        Create AWS config with sensible defaults.

        Args:
            region: AWS region (defaults to us-east-1)
            service_name: Service name (defaults to supply-graph-ai)
            **kwargs: Additional configuration overrides

        Returns:
            AWSDeploymentConfig instance
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
        provider_config = kwargs.pop("provider_config", {})

        # Remaining kwargs go to top-level config
        config_kwargs = {
            "provider": DeploymentProvider.AWS,
            "environment": kwargs.pop("environment", "production"),
            "region": region,  # Will default to us-east-1 in __post_init__
            "service": ServiceConfig(**service_kwargs),
            "provider_config": provider_config,
        }

        # Any remaining kwargs are invalid
        if kwargs:
            raise DeploymentConfigError(
                f"Unexpected keyword arguments: {list(kwargs.keys())}. "
                "Use 'provider_config' for AWS-specific settings."
            )

        return cls(**config_kwargs)
