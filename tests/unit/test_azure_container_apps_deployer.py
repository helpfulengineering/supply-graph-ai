"""Unit tests for AzureContainerAppsDeployer.deploy() command construction.

These exercise the exact bugs found when wiring this deployer into CI for the
first time: ``_check_service_exists`` was referenced but never defined,
``--env-vars`` was passed as a single space-joined string instead of separate
argv tokens (azure CLI's nargs='*' parses each list element independently),
and ``update`` was given create-only flags (``--env-vars``, ``--target-port``,
``--ingress``, ``--environment``, ``--registry-*``) that ``az containerapp
update`` rejects. No live Azure calls are made — subprocess.run is mocked.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from deploy.providers.azure.config import AzureDeploymentConfig
from deploy.providers.azure.container_apps import AzureContainerAppsDeployer


def _config(**env_overrides):
    data = {
        "provider": "azure",
        "environment": "production",
        "region": "eastus",
        "service": {
            "name": "openhardwaremanager",
            "image": "touchthesun/openhardwaremanager:0.8.6",
            "environment_vars": {"ENVIRONMENT": "production", **env_overrides},
        },
        "providers": {
            "azure": {
                "resource_group": "project_data_rg",
                "subscription_id": "test-sub",
            }
        },
    }
    return AzureDeploymentConfig.from_dict(data)


def _mock_run(returncode_by_call):
    """subprocess.run mock that returns successive returncodes per call."""
    calls = []

    def _run(command, capture_output, text, check):
        calls.append(command)
        result = MagicMock()
        result.returncode = returncode_by_call(len(calls) - 1)
        result.stdout = "https://openhardwaremanager.example.azurecontainerapps.io"
        result.stderr = ""
        return result

    return _run, calls


def test_check_service_exists_true_when_az_show_succeeds():
    deployer = AzureContainerAppsDeployer(_config())
    run_fn, calls = _mock_run(lambda i: 0)
    with patch(
        "deploy.providers.azure.container_apps.subprocess.run", side_effect=run_fn
    ):
        assert deployer._check_service_exists() is True
    assert calls[0][:4] == ["az", "containerapp", "show", "--name"]


def test_check_service_exists_false_when_az_show_fails():
    deployer = AzureContainerAppsDeployer(_config())
    run_fn, _ = _mock_run(lambda i: 1)
    with patch(
        "deploy.providers.azure.container_apps.subprocess.run", side_effect=run_fn
    ):
        assert deployer._check_service_exists() is False


def _deploy_with_existing_app(exists: bool, env_overrides=None):
    """Run deploy() with resource-group/env checks always succeeding, and the
    show-for-existence check returning `exists`. Returns the deploy command argv."""
    deployer = AzureContainerAppsDeployer(_config(**(env_overrides or {})))

    call_log = []

    def _run(command, capture_output, text, check):
        call_log.append(command)
        result = MagicMock()
        result.stdout = "https://openhardwaremanager.example.azurecontainerapps.io"
        result.stderr = ""
        if command[:3] == ["az", "containerapp", "show"] and "--query" not in command:
            result.returncode = 0 if exists else 1
        else:
            result.returncode = 0
        return result

    with patch(
        "deploy.providers.azure.container_apps.subprocess.run", side_effect=_run
    ):
        deployer.deploy()

    deploy_calls = [
        c for c in call_log if c[2] in ("create", "update") and c[1] == "containerapp"
    ]
    assert len(deploy_calls) == 1
    return deploy_calls[0]


def test_deploy_update_path_uses_set_env_vars_not_env_vars():
    args = _deploy_with_existing_app(exists=True, env_overrides={"CORS_ORIGINS": "*"})

    assert args[2] == "update"
    assert "--env-vars" not in args
    assert "--set-env-vars" in args
    assert "--target-port" not in args
    assert "--ingress" not in args
    assert "--environment" not in args


def test_deploy_update_path_passes_each_env_var_as_separate_token():
    args = _deploy_with_existing_app(
        exists=True,
        env_overrides={"CORS_ORIGINS": "*", "STORAGE_PROVIDER": "azure_blob"},
    )

    idx = args.index("--set-env-vars")
    env_tokens = args[idx + 1 :]
    # Each KEY=VALUE pair must be its own argv element, not one joined string.
    assert "ENVIRONMENT=production" in env_tokens
    assert "CORS_ORIGINS=*" in env_tokens
    assert "STORAGE_PROVIDER=azure_blob" in env_tokens
    assert not any(" " in tok for tok in env_tokens)


def test_deploy_create_path_uses_env_vars_and_ingress_flags():
    args = _deploy_with_existing_app(exists=False, env_overrides={"CORS_ORIGINS": "*"})

    assert args[2] == "create"
    assert "--env-vars" in args
    assert "--set-env-vars" not in args
    assert "--target-port" in args
    assert "--ingress" in args
    assert "--environment" not in args  # not set in this fixture's provider_config
