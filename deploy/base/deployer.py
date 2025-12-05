"""
Base deployer interface for cloud-agnostic deployment.

All provider-specific deployers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

from .config import BaseDeploymentConfig

logger = logging.getLogger(__name__)


class BaseDeployer(ABC):
    """Base class for cloud provider deployers."""

    def __init__(self, config: BaseDeploymentConfig):
        """
        Initialize deployer with configuration.

        Args:
            config: Deployment configuration
        """
        self.config = config
        self.config.validate()
        logger.info(f"Initialized {self.__class__.__name__} for provider {config.provider.value}")

    @abstractmethod
    def setup(self) -> None:
        """
        Setup cloud resources (IAM, storage, etc.).

        This method should be idempotent - calling it multiple times
        should not cause errors if resources already exist.

        Raises:
            DeploymentError: If setup fails
        """
        pass

    @abstractmethod
    def deploy(self) -> str:
        """
        Deploy service and return service URL.

        Returns:
            Service URL (e.g., https://service.example.com)

        Raises:
            DeploymentError: If deployment fails
        """
        pass

    @abstractmethod
    def get_service_url(self, service_name: Optional[str] = None) -> str:
        """
        Get the deployed service URL.

        Args:
            service_name: Optional service name (defaults to config.service.name)

        Returns:
            Service URL

        Raises:
            DeploymentError: If service not found
        """
        pass

    @abstractmethod
    def update(self) -> str:
        """
        Update existing deployment.

        Returns:
            Service URL

        Raises:
            DeploymentError: If update fails
        """
        pass

    @abstractmethod
    def delete(self, service_name: Optional[str] = None) -> None:
        """
        Delete deployment.

        Args:
            service_name: Optional service name (defaults to config.service.name)

        Raises:
            DeploymentError: If deletion fails
        """
        pass

    @abstractmethod
    def get_status(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get deployment status.

        Args:
            service_name: Optional service name (defaults to config.service.name)

        Returns:
            Dictionary with status information (e.g., {"status": "running", "url": "..."})

        Raises:
            DeploymentError: If status check fails
        """
        pass

    def validate_config(self) -> None:
        """
        Validate deployment configuration.

        This is called automatically during initialization, but can be
        called manually to check configuration before deployment.

        Raises:
            DeploymentConfigError: If configuration is invalid
        """
        self.config.validate()

