"""
AWS (Amazon Web Services) deployment provider.

This module provides AWS-specific deployment configuration and deployers.
"""

from .config import AWSDeploymentConfig
from .fargate import AWSFargateDeployer, DeploymentError

__all__ = [
    "AWSDeploymentConfig",
    "AWSFargateDeployer",
    "DeploymentError",
]

