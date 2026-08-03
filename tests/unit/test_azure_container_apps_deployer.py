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


def _config(_service_overrides=None, **env_overrides):
    data = {
        "provider": "azure",
        "environment": "production",
        "region": "eastus",
        "service": {
            "name": "openhardwaremanager",
            "image": "touchthesun/openhardwaremanager:0.8.6",
            "environment_vars": {"ENVIRONMENT": "production", **env_overrides},
            **(_service_overrides or {}),
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


def _deploy_calls(exists: bool, env_overrides=None, service_overrides=None):
    """Run deploy() with resource-group/env checks always succeeding, and the
    show-for-existence check returning `exists`. Returns (deploy argv, all argv)."""
    deployer = AzureContainerAppsDeployer(
        _config(service_overrides, **(env_overrides or {}))
    )

    call_log = []

    def _run(command, capture_output, text, check):
        call_log.append(command)
        result = MagicMock()
        # `az ... --query properties.configuration.ingress.fqdn -o tsv` returns a
        # bare hostname; get_service_url() is what adds the scheme.
        result.stdout = "openhardwaremanager.example.azurecontainerapps.io"
        result.stderr = ""
        if command[:3] == ["az", "containerapp", "show"] and "--query" not in command:
            result.returncode = 0 if exists else 1
        else:
            result.returncode = 0
        return result

    with patch(
        "deploy.providers.azure.container_apps.subprocess.run", side_effect=_run
    ):
        url = deployer.deploy()

    deploy_calls = [
        c for c in call_log if c[2] in ("create", "update") and c[1] == "containerapp"
    ]
    assert len(deploy_calls) == 1
    return deploy_calls[0], call_log, url


def _deploy_with_existing_app(exists: bool, env_overrides=None):
    args, _, _ = _deploy_calls(exists, env_overrides)
    return args


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


# --- Regression: web-service deploys must be byte-identical to before -------
#
# Ingress-less support (worker apps) touched the shared argv builder, so these
# pin the ENTIRE command for a normal web service. A diff here means a change
# leaked into the API or frontend deploy path.


def test_web_service_create_argv_is_unchanged():
    args, _, _ = _deploy_calls(exists=False, env_overrides={"CORS_ORIGINS": "*"})

    assert args == [
        "az",
        "containerapp",
        "create",
        "--name",
        "openhardwaremanager",
        "--resource-group",
        "project_data_rg",
        "--image",
        "touchthesun/openhardwaremanager:0.8.6",
        "--cpu",
        "2",
        "--memory",
        "4.0Gi",
        "--min-replicas",
        "1",
        "--max-replicas",
        "100",
        "--target-port",
        "8080",
        "--ingress",
        "external",
        "--env-vars",
        "ENVIRONMENT=production",
        "CORS_ORIGINS=*",
    ]


def test_web_service_update_argv_is_unchanged():
    args, _, _ = _deploy_calls(exists=True, env_overrides={"CORS_ORIGINS": "*"})

    assert args == [
        "az",
        "containerapp",
        "update",
        "--name",
        "openhardwaremanager",
        "--resource-group",
        "project_data_rg",
        "--image",
        "touchthesun/openhardwaremanager:0.8.6",
        "--cpu",
        "2",
        "--memory",
        "4.0Gi",
        "--min-replicas",
        "1",
        "--max-replicas",
        "100",
        "--set-env-vars",
        "ENVIRONMENT=production",
        "CORS_ORIGINS=*",
    ]


def test_frontend_shaped_service_still_gets_ingress():
    """The frontend deploys with its own cpu/memory/port but is still a web app."""
    args, _, _ = _deploy_calls(
        exists=True,
        service_overrides={"cpu": 0.5, "memory": "1Gi", "port": 8080},
    )

    assert "--cpu" in args and args[args.index("--cpu") + 1] == "0.5"
    assert args[args.index("--memory") + 1] == "1.0Gi"
    # update never carried ingress flags; that must stay true.
    assert "--ingress" not in args and "--target-port" not in args


def test_ingress_enabled_defaults_true_when_config_omits_it():
    assert _config().service.ingress_enabled is True
    assert _config().service.command is None
    assert _config().service.args is None


# --- Ingress-less (worker) apps ---------------------------------------------

_WORKER = {
    "ingress_enabled": False,
    "command": ["/usr/local/bin/docker-entrypoint.sh"],
    "args": ["worker"],
}


def test_worker_create_omits_ingress_flags():
    args, _, _ = _deploy_calls(exists=False, service_overrides=_WORKER)

    assert args[2] == "create"
    # No --ingress at all means Azure creates the app with ingress disabled.
    assert "--ingress" not in args
    assert "--target-port" not in args
    assert "--env-vars" in args


def test_worker_deploy_passes_command_and_args_as_separate_tokens():
    for exists in (True, False):
        args, _, _ = _deploy_calls(exists=exists, service_overrides=_WORKER)

        assert (
            args[args.index("--command") + 1] == "/usr/local/bin/docker-entrypoint.sh"
        )
        assert args[args.index("--args") + 1] == "worker"
        # nargs='*' flags need one argv element per value, never a joined string.
        assert not any(" " in tok for tok in args)


def test_worker_deploy_never_looks_up_an_fqdn():
    """An ingress-less app has no FQDN; querying for one would fail a deploy
    that actually succeeded."""
    _, call_log, url = _deploy_calls(exists=True, service_overrides=_WORKER)

    assert url == ""
    assert not any("properties.configuration.ingress.fqdn" in c for c in call_log)


def test_web_service_deploy_still_returns_its_url():
    _, call_log, url = _deploy_calls(exists=True)

    assert url == "https://openhardwaremanager.example.azurecontainerapps.io"
    assert any("properties.configuration.ingress.fqdn" in c for c in call_log)


def test_fqdn_from_app_data_handles_apps_with_and_without_ingress():
    with_ingress = {
        "properties": {"configuration": {"ingress": {"fqdn": "app.example.io"}}}
    }
    assert (
        AzureContainerAppsDeployer._fqdn_from_app_data(with_ingress)
        == "https://app.example.io"
    )
    # A worker's `az containerapp show` reports ingress: null.
    assert (
        AzureContainerAppsDeployer._fqdn_from_app_data(
            {"properties": {"configuration": {"ingress": None}}}
        )
        == ""
    )
    assert AzureContainerAppsDeployer._fqdn_from_app_data({}) == ""
