"""Mint Redis connection URLs as Azure Container App secrets.

One Azure Cache for Redis instance backs both the catalogue cache and the
Celery broker/results, split by database (0=cache, 1=broker, 2=results) — the
split ``docker-compose.yml`` uses. The access key is never checked in: the
deploy reads it from Azure and builds the URLs here, so the credential lives in
exactly one place, rotating it needs no repo change, and two container apps
pointed at the same instance cannot drift apart.

The non-secret half (host, port, database indices) is declared in
``config/environments/<env>.toml`` under ``[redis]`` and read by
``src.config.schema.redis_deploy_config``.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping
from urllib.parse import quote

# Container App secret names. These are referenced by env vars as
# `secretref:<name>`, so renaming one is a breaking deploy change.
SECRET_CACHE_URL = "cache-redis-url"
SECRET_JOB_BROKER_URL = "job-broker-url"
SECRET_JOB_RESULT_BACKEND = "job-result-backend"

# Env var -> secret name. The env var carries `secretref:<name>`, never a value.
REDIS_SECRET_ENV_REFS: Dict[str, str] = {
    "CACHE_REDIS_URL": SECRET_CACHE_URL,
    "JOB_BROKER_URL": SECRET_JOB_BROKER_URL,
    "JOB_RESULT_BACKEND": SECRET_JOB_RESULT_BACKEND,
}

_REQUIRED_KEYS = ("host", "port", "cache_db", "broker_db", "results_db")


class RedisConfigError(ValueError):
    """Raised when the [redis] table is missing fields needed to build a URL."""


def _redis_url(host: str, port: Any, db: Any, access_key: str) -> str:
    """One ``rediss://`` URL with TLS verification explicitly required.

    Two details that are easy to get wrong and fail quietly:

    * ``?ssl_cert_reqs=required`` is mandatory. kombu parses a bare ``rediss://``
      URL to ``CERT_NONE`` — no error, no warning, certificate verification
      silently off.
    * The key is percent-encoded. Azure Redis access keys are base64, whose
      alphabet includes ``/`` and ``+``; an unencoded ``/`` terminates the
      userinfo section and silently truncates the password. redis-py unquotes
      the password, so encoding here round-trips correctly.
    """
    return (
        f"rediss://:{quote(access_key, safe='')}@{host}:{port}/{db}"
        "?ssl_cert_reqs=required"
    )


def build_redis_secret_values(
    redis_config: Mapping[str, Any], access_key: str
) -> Dict[str, str]:
    """Map of secret name -> connection URL for the three Redis databases.

    Args:
        redis_config: the ``[redis]`` table (host, port, and db indices).
        access_key: the Redis access key, fetched from Azure at deploy time.

    Raises:
        RedisConfigError: if the table is incomplete or the key is empty. Both
            are deploy-stopping: a partial URL would "succeed" and then fail at
            runtime as a connection error far from its cause.
    """
    missing = [key for key in _REQUIRED_KEYS if redis_config.get(key) is None]
    if missing:
        raise RedisConfigError(
            f"[redis] config is missing required key(s): {', '.join(missing)}"
        )
    if not access_key or not access_key.strip():
        raise RedisConfigError("Redis access key is empty; refusing to build URLs")

    host = redis_config["host"]
    port = redis_config["port"]
    return {
        SECRET_CACHE_URL: _redis_url(host, port, redis_config["cache_db"], access_key),
        SECRET_JOB_BROKER_URL: _redis_url(
            host, port, redis_config["broker_db"], access_key
        ),
        SECRET_JOB_RESULT_BACKEND: _redis_url(
            host, port, redis_config["results_db"], access_key
        ),
    }


def redis_secret_env_vars() -> Dict[str, str]:
    """Env vars that reference the minted secrets, never their values."""
    return {
        env_var: f"secretref:{secret}"
        for env_var, secret in REDIS_SECRET_ENV_REFS.items()
    }
