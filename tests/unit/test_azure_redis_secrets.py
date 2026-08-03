"""Unit tests for minting Redis connection URLs as Container App secrets.

No live Azure calls — subprocess.run is mocked. The URL builder is pure, so
most of this is exact-string assertion on what the deploy would write.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from deploy.providers.azure.config import AzureDeploymentConfig
from deploy.providers.azure.container_apps import (
    AzureContainerAppsDeployer,
    DeploymentError,
)
from deploy.providers.azure.redis_secrets import (
    SECRET_CACHE_URL,
    SECRET_JOB_BROKER_URL,
    SECRET_JOB_RESULT_BACKEND,
    RedisConfigError,
    build_redis_secret_values,
    redis_secret_env_vars,
)
from src.config.schema import redis_deploy_config

_REDIS_CONFIG = {
    "resource_name": "ohm-cache",
    "host": "ohm-cache.redis.cache.windows.net",
    "port": 6380,
    "cache_db": 0,
    "broker_db": 1,
    "results_db": 2,
}


def _deployer():
    config = AzureDeploymentConfig.from_dict(
        {
            "provider": "azure",
            "environment": "production",
            "region": "eastus",
            "service": {"name": "openhardwaremanager", "image": "img:1"},
            "providers": {
                "azure": {
                    "resource_group": "project_data_rg",
                    "subscription_id": "test-sub",
                }
            },
        }
    )
    return AzureContainerAppsDeployer(config)


# --- URL construction --------------------------------------------------------


def test_builds_one_url_per_database():
    secrets = build_redis_secret_values(_REDIS_CONFIG, "plainkey")

    host = "ohm-cache.redis.cache.windows.net:6380"
    assert secrets == {
        SECRET_CACHE_URL: f"rediss://:plainkey@{host}/0?ssl_cert_reqs=required",
        SECRET_JOB_BROKER_URL: f"rediss://:plainkey@{host}/1?ssl_cert_reqs=required",
        SECRET_JOB_RESULT_BACKEND: (
            f"rediss://:plainkey@{host}/2?ssl_cert_reqs=required"
        ),
    }


def test_every_url_requires_tls_verification():
    """A bare rediss:// URL parses to CERT_NONE under kombu — silently insecure."""
    for url in build_redis_secret_values(_REDIS_CONFIG, "k").values():
        assert url.startswith("rediss://")
        assert url.endswith("?ssl_cert_reqs=required")


def test_access_key_is_percent_encoded():
    """Azure Redis keys are base64: '/' and '+' appear and MUST be encoded.

    An unencoded '/' terminates the URL's userinfo section and silently
    truncates the password, producing an auth failure far from its cause.
    """
    secrets = build_redis_secret_values(_REDIS_CONFIG, "ab/cd+ef=")

    broker = secrets[SECRET_JOB_BROKER_URL]
    assert "ab%2Fcd%2Bef%3D" in broker
    # The raw key must not survive anywhere in the URL.
    assert "ab/cd+ef=" not in broker
    # Exactly one '@' and one '/' after the host, or the password leaked into
    # the path and the db index is wrong.
    assert broker.count("@") == 1
    assert broker.split("@", 1)[1].count("/") == 1


def test_encoded_key_round_trips_through_a_url_parser():
    from urllib.parse import unquote, urlsplit

    key = "ab/cd+ef=="
    url = build_redis_secret_values(_REDIS_CONFIG, key)[SECRET_JOB_BROKER_URL]

    parts = urlsplit(url)
    assert unquote(parts.password) == key
    assert parts.hostname == "ohm-cache.redis.cache.windows.net"
    assert parts.port == 6380
    assert parts.path == "/1"


# --- Refusing to build something broken --------------------------------------


@pytest.mark.parametrize(
    "missing", ["host", "port", "cache_db", "broker_db", "results_db"]
)
def test_incomplete_config_is_refused(missing):
    config = {key: value for key, value in _REDIS_CONFIG.items() if key != missing}
    with pytest.raises(RedisConfigError, match=missing):
        build_redis_secret_values(config, "key")


def test_empty_access_key_is_refused():
    with pytest.raises(RedisConfigError, match="empty"):
        build_redis_secret_values(_REDIS_CONFIG, "   ")


def test_db_index_zero_is_not_treated_as_missing():
    """cache_db = 0 is falsy; a truthiness check here would drop it."""
    assert build_redis_secret_values(_REDIS_CONFIG, "k")[SECRET_CACHE_URL].endswith(
        "/0?ssl_cert_reqs=required"
    )


# --- Env var wiring ----------------------------------------------------------


def test_env_vars_reference_secrets_and_never_carry_values():
    env_vars = redis_secret_env_vars()

    assert env_vars == {
        "CACHE_REDIS_URL": "secretref:cache-redis-url",
        "JOB_BROKER_URL": "secretref:job-broker-url",
        "JOB_RESULT_BACKEND": "secretref:job-result-backend",
    }
    assert not any("rediss://" in value for value in env_vars.values())


def test_jobs_enabled_is_not_implied_by_wiring_the_broker_url():
    """Setting JOB_BROKER_URL must not switch async jobs on by itself.

    jobs_available() is `jobs_enabled AND job_broker_url`, so the endpoints stay
    503 until JOBS_ENABLED is turned on deliberately.
    """
    assert "JOBS_ENABLED" not in redis_secret_env_vars()


# --- Reading the config surface ----------------------------------------------


def test_production_redis_config_declares_the_documented_db_split():
    config = redis_deploy_config("production")

    assert config["cache_db"] == 0
    assert config["broker_db"] == 1
    assert config["results_db"] == 2
    # The credential must never be checked in.
    assert not any("key" in name.lower() for name in config)


def test_absent_environment_yields_no_redis_management():
    assert redis_deploy_config("no-such-environment") == {}


def test_redis_table_is_not_leaked_into_backend_env_vars():
    """[redis] is deploy coordinates, not container env — it must not be applied."""
    from src.config.schema import deploy_env_vars

    env_vars = deploy_env_vars("production")

    assert "REDIS" not in env_vars
    assert not any(key.startswith("REDIS_") for key in env_vars)
    # And nothing resembling a connection string got in.
    assert not any("rediss://" in value for value in env_vars.values())


# --- The deploy wires it in the only order that works ------------------------


def _run_deploy_script(record):
    """Run deploy_azure.py main() with every az call mocked."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_deploy_azure_under_test",
        _REPO_ROOT / "deploy" / "scripts" / "deploy_azure.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    argv = [
        "deploy_azure.py",
        "--image",
        "touchthesun/openhardwaremanager@sha256:abc",
        "--subscription-id",
        "test-sub",
        "--environment",
        "production",
    ]
    with (
        patch.object(sys, "argv", argv),
        patch(
            "deploy.providers.azure.container_apps.subprocess.run",
            side_effect=_run_mock(record=record),
        ),
    ):
        return module.main()


def test_deploy_sets_secrets_before_the_update_that_references_them():
    """A secretRef to a secret that does not exist yet fails the update."""
    calls = []
    assert _run_deploy_script(calls) == 0

    kinds = [
        (
            "list-keys"
            if command[:3] == ["az", "redis", "list-keys"]
            else (
                "secret-set"
                if command[:4] == ["az", "containerapp", "secret", "set"]
                else (
                    "app-update"
                    if command[:3] == ["az", "containerapp", "update"]
                    else None
                )
            )
        )
        for command in calls
    ]
    ordered = [kind for kind in kinds if kind]

    assert ordered.index("list-keys") < ordered.index("secret-set")
    assert ordered.index("secret-set") < ordered.index("app-update")


def test_deploy_applies_secretrefs_never_values():
    calls = []
    assert _run_deploy_script(calls) == 0

    update = next(c for c in calls if c[:3] == ["az", "containerapp", "update"])
    env_tokens = update[update.index("--set-env-vars") + 1 :]

    assert "JOB_BROKER_URL=secretref:job-broker-url" in env_tokens
    assert "JOB_RESULT_BACKEND=secretref:job-result-backend" in env_tokens
    # No secret value is ever passed as an env var. Whether jobs are ENABLED is
    # a separate decision, declared in the environment's config file — see
    # test_jobs_enabled_is_not_implied_by_wiring_the_broker_url.
    assert not any("rediss://" in token for token in env_tokens)


# --- Azure interaction -------------------------------------------------------


def _run_mock(returncode=0, stdout="thekey", record=None):
    def _run(command, capture_output, text, check):
        if record is not None:
            record.append(command)
        result = MagicMock()
        result.returncode = returncode
        result.stdout = stdout
        result.stderr = "boom" if returncode else ""
        return result

    return _run


def test_fetch_redis_access_key_queries_the_primary_key():
    calls = []
    with patch(
        "deploy.providers.azure.container_apps.subprocess.run",
        side_effect=_run_mock(record=calls),
    ):
        assert _deployer().fetch_redis_access_key("ohm-cache") == "thekey"

    command = calls[0]
    assert command[:3] == ["az", "redis", "list-keys"]
    assert "primaryKey" in command
    assert "ohm-cache" in command


def test_fetch_redis_access_key_fails_loudly_when_az_fails():
    with patch(
        "deploy.providers.azure.container_apps.subprocess.run",
        side_effect=_run_mock(returncode=1),
    ):
        with pytest.raises(DeploymentError, match="Could not read the access key"):
            _deployer().fetch_redis_access_key("ohm-cache")


def test_fetch_redis_access_key_fails_loudly_on_an_empty_key():
    """An empty key must not silently become an anonymous connection URL."""
    with patch(
        "deploy.providers.azure.container_apps.subprocess.run",
        side_effect=_run_mock(stdout="  \n"),
    ):
        with pytest.raises(DeploymentError, match="empty key"):
            _deployer().fetch_redis_access_key("ohm-cache")


def test_set_secrets_passes_each_secret_as_its_own_token():
    calls = []
    with patch(
        "deploy.providers.azure.container_apps.subprocess.run",
        side_effect=_run_mock(record=calls),
    ):
        _deployer().set_secrets({"job-broker-url": "rediss://:k@h:6380/1"})

    command = calls[0]
    assert command[:4] == ["az", "containerapp", "secret", "set"]
    assert (
        command[command.index("--secrets") + 1] == "job-broker-url=rediss://:k@h:6380/1"
    )


def test_set_secrets_never_logs_secret_values(caplog):
    import logging

    caplog.set_level(logging.DEBUG)
    with patch(
        "deploy.providers.azure.container_apps.subprocess.run", side_effect=_run_mock()
    ):
        _deployer().set_secrets(build_redis_secret_values(_REDIS_CONFIG, "s3cr3tkey"))

    assert "s3cr3tkey" not in caplog.text
    assert "rediss://" not in caplog.text
    # Names are safe and useful.
    assert SECRET_JOB_BROKER_URL in caplog.text


def test_set_secrets_is_a_noop_for_an_empty_mapping():
    calls = []
    with patch(
        "deploy.providers.azure.container_apps.subprocess.run",
        side_effect=_run_mock(record=calls),
    ):
        _deployer().set_secrets({})

    assert calls == []


def test_set_secrets_raises_when_az_fails():
    with patch(
        "deploy.providers.azure.container_apps.subprocess.run",
        side_effect=_run_mock(returncode=1),
    ):
        with pytest.raises(DeploymentError, match="Failed to set secrets"):
            _deployer().set_secrets({"job-broker-url": "rediss://:k@h:6380/1"})
