"""Regression: deployment configs must never silently omit CORS_ORIGINS.

src/config/settings.py defaults CORS_ORIGINS to an empty list (deny all) in
production when unset, which makes every browser CORS preflight to the
deployed API fail with 400 before the request ever reaches a route handler.

GCP/AWS/Azure each implement their own from_dict() (none delegate to
BaseDeploymentConfig.from_dict() via super()), so the default must be applied
via the shared apply_cors_origins_default() helper in every provider's
from_dict(), not just the base class — exercise all three here, plus the
base class directly since it's also a valid (if currently unused by the
concrete deployers) construction path.
"""

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest

from deploy.base.config import BaseDeploymentConfig
from deploy.providers.aws.config import AWSDeploymentConfig
from deploy.providers.azure.config import AzureDeploymentConfig
from deploy.providers.gcp.config import GCPDeploymentConfig

_PROVIDER_CONFIG = {
    "gcp": {"project_id": "my-test-project"},
    "aws": {},
    "azure": {"resource_group": "test-rg", "subscription_id": "test-sub"},
}


def _data(provider, **overrides):
    data = {
        "provider": provider,
        "environment": "production",
        "service": {
            "name": "supply-graph-ai",
            "image": "ghcr.io/example/supply-graph-ai:latest",
            "environment_vars": {},
        },
        "providers": {provider: _PROVIDER_CONFIG[provider]},
    }
    data.update(overrides)
    return data


CONFIG_CLASSES = [
    (BaseDeploymentConfig, "gcp"),
    (AzureDeploymentConfig, "azure"),
    (AWSDeploymentConfig, "aws"),
    (GCPDeploymentConfig, "gcp"),
]


@pytest.mark.parametrize("config_cls,provider", CONFIG_CLASSES)
def test_cors_origins_defaults_to_wildcard_when_omitted(config_cls, provider):
    config = config_cls.from_dict(_data(provider))
    assert config.service.environment_vars["CORS_ORIGINS"] == "*"


@pytest.mark.parametrize("config_cls,provider", CONFIG_CLASSES)
def test_cors_origins_respects_explicit_value(config_cls, provider):
    data = _data(provider)
    data["service"]["environment_vars"] = {"CORS_ORIGINS": "https://app.example.com"}
    config = config_cls.from_dict(data)
    assert config.service.environment_vars["CORS_ORIGINS"] == "https://app.example.com"


@pytest.mark.parametrize("config_cls,provider", CONFIG_CLASSES)
def test_cors_origins_default_applies_regardless_of_environment(config_cls, provider):
    data = _data(provider, environment="development")
    config = config_cls.from_dict(data)
    assert config.service.environment_vars["CORS_ORIGINS"] == "*"


def test_gcp_with_defaults_defaults_cors_origins():
    """deploy_gcp.py (the only real, non-test deploy script in this repo)
    constructs config via with_defaults(), not from_dict() — must also default."""
    config = GCPDeploymentConfig.with_defaults(
        project_id="my-test-project",
        environment_vars={"ENVIRONMENT": "production"},
    )
    assert config.service.environment_vars["CORS_ORIGINS"] == "*"


def test_azure_with_defaults_defaults_cors_origins():
    config = AzureDeploymentConfig.with_defaults(
        resource_group="test-rg",
        subscription_id="test-sub",
    )
    assert config.service.environment_vars["CORS_ORIGINS"] == "*"


def test_aws_with_defaults_defaults_cors_origins():
    config = AWSDeploymentConfig.with_defaults()
    assert config.service.environment_vars["CORS_ORIGINS"] == "*"
