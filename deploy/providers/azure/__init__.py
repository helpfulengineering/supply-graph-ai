"""
Azure (Microsoft Azure) deployment provider.

This module provides Azure-specific deployment configuration and deployers.
"""

from .config import AzureDeploymentConfig
from .container_apps import AzureContainerAppsDeployer, DeploymentError

__all__ = [
    "AzureDeploymentConfig",
    "AzureContainerAppsDeployer",
    "DeploymentError",
]
