"""
Base deployment abstraction layer.

This module provides the base classes and interfaces for cloud-agnostic deployment.
All provider-specific deployers should inherit from BaseDeployer.
"""

from .deployer import BaseDeployer
from .config import BaseDeploymentConfig, DeploymentConfigError

__all__ = [
    "BaseDeployer",
    "BaseDeploymentConfig",
    "DeploymentConfigError",
]

