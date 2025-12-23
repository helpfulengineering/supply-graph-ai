"""
Base deployment abstraction layer.

This module provides the base classes and interfaces for cloud-agnostic deployment.
All provider-specific deployers should inherit from BaseDeployer.
"""

from .config import BaseDeploymentConfig, DeploymentConfigError
from .deployer import BaseDeployer

__all__ = [
    "BaseDeployer",
    "BaseDeploymentConfig",
    "DeploymentConfigError",
]
