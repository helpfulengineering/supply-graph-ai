"""Typed application configuration — Slice 1.

Single source of truth for a first, narrow slice of settings: the storage
target (provider / account / container), the runtime ``environment``, the OKW
facility source, and CORS. Non-secret values are layered from the checked-in
per-environment file ``config/environments/<environment>.toml``; process
environment variables (secrets and overrides) take precedence.

Layering (highest priority first): init kwargs → process env → per-env TOML →
field defaults. Secrets (``AZURE_STORAGE_KEY`` and friends) live only in the
process environment / ``.env`` / Azure ``secretRef`` — never in the TOML files.

This module deliberately covers only Slice 1. The remaining settings still live
in :mod:`src.config.settings`; they migrate incrementally in later slices.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

logger = logging.getLogger(__name__)

_CONFIG_ENV_DIR = (
    Path(__file__).resolve().parent.parent.parent / "config" / "environments"
)


def _find_project_env() -> Optional[Path]:
    """Find .env by walking up from this file (mirrors storage_config)."""
    try:
        current = Path(__file__).resolve().parent
        for _ in range(6):
            env_file = current / ".env"
            if env_file.is_file():
                return env_file
            current = current.parent
            if not current or current == current.parent:
                break
    except Exception:
        pass
    return None


# Populate os.environ from the project-root .env regardless of cwd, so config is
# correct when `ohm` runs from any directory.
_env_path = _find_project_env()
if _env_path:
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()


def strip_quotes(value: Optional[str]) -> Optional[str]:
    """Strip surrounding whitespace + quotes; empty becomes ``None``.

    ``docker run --env-file`` passes values verbatim (quotes included), while
    python-dotenv (docker-compose, ``load_dotenv``) strips them. Normalising
    here makes both invocation styles produce identical values.
    """
    if value is None:
        return None
    stripped = value.strip().strip("\"'")
    return stripped if stripped else None


def resolve_cors_origins(
    raw: Optional[str], environment: str, *, log: bool = False
) -> List[str]:
    """Resolve the raw ``CORS_ORIGINS`` string into a list of allowed origins.

    Behaviour mirrors the historical logic in ``settings.py``: unset defaults to
    ``[]`` in production (deny) and ``["*"]`` elsewhere (allow-all for dev
    convenience); ``"*"`` is an explicit wildcard; otherwise a comma-separated
    allowlist. Pass ``log=True`` to emit the operational warnings once.
    """
    if raw is None or raw.strip() == "":
        if environment == "production":
            if log:
                logger.warning(
                    "CORS_ORIGINS not set in production. No CORS origins allowed "
                    "by default. Set CORS_ORIGINS to allow specific origins."
                )
            return []
        if log:
            logger.info(
                "CORS_ORIGINS not set. Allowing all origins in development mode. "
                "Set CORS_ORIGINS to restrict origins."
            )
        return ["*"]

    if raw.strip() == "*":
        if environment == "production" and log:
            logger.warning(
                "CORS_ORIGINS is set to '*' in production. This allows all origins. "
                "Consider restricting to specific origins for better security."
            )
        return ["*"]

    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not origins and log:
        logger.warning("CORS_ORIGINS is set but empty. No CORS origins allowed.")
    return origins


class _NormalizingEnvSource(EnvSettingsSource):
    """Env source that strips surrounding quotes/whitespace from every value.

    Keeps ``docker --env-file`` and dotenv invocations byte-identical (see
    :func:`strip_quotes`).
    """

    def prepare_field_value(self, field_name, field, value, value_is_complex):
        return super().prepare_field_value(
            field_name, field, strip_quotes(value), value_is_complex
        )


class Settings(BaseSettings):
    """Slice-1 typed configuration.

    Field names map case-insensitively to their historical env-var names
    (``storage_provider`` ← ``STORAGE_PROVIDER``) and to the snake_case keys in
    the per-environment TOML files.
    """

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    environment: str = Field(
        default="development",
        description="Runtime environment; selects config/environments/<env>.toml.",
    )
    storage_provider: str = Field(
        default="local",
        description="Storage backend: local | azure_blob | aws_s3 | gcs.",
    )
    azure_storage_account: Optional[str] = Field(
        default=None,
        description="Azure Blob storage account name (when storage_provider=azure_blob).",
    )
    azure_storage_container: Optional[str] = Field(
        default=None,
        description="Azure Blob container name.",
    )
    azure_storage_key: Optional[str] = Field(
        default=None,
        description="Azure Blob access key.",
        json_schema_extra={"secret": True},  # env/.env / secretRef only, never TOML
    )
    okw_source: Optional[str] = Field(
        default=None,  # unset resolves via okw_source_resolved
        description="OKW facility source: storage | mom. Unset resolves to storage (Slice 1).",
    )
    cors_origins: Optional[str] = Field(
        default=None,  # raw; parse via cors_allow_origins
        description="CORS allowed origins: '*' or a comma-separated list.",
    )

    @field_validator("environment")
    @classmethod
    def _normalize_environment(cls, value: str) -> str:
        return (value or "development").strip().lower()

    @property
    def okw_source_resolved(self) -> str:
        """The effective OKW facility source: ``"storage"`` or ``"mom"``.

        Unset falls back to ``"storage"``; unknown values fall back to
        ``"storage"`` with a warning (behaviour-preserving for Slice 1).
        """
        source = self.okw_source or "storage"
        if source not in ("storage", "mom"):
            logger.warning(
                "Unknown OKW_SOURCE value %r — falling back to 'storage'", source
            )
            return "storage"
        return source

    @property
    def cors_allow_origins(self) -> List[str]:
        return resolve_cors_origins(self.cors_origins, self.environment)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        # Resolve the environment (env var wins) to pick the per-env TOML file.
        env_name = (
            strip_quotes(os.environ.get("ENVIRONMENT")) or "development"
        ).lower()
        normalized_env = _NormalizingEnvSource(settings_cls)

        toml_path = _CONFIG_ENV_DIR / f"{env_name}.toml"
        if toml_path.is_file():
            toml_source = TomlConfigSettingsSource(settings_cls, toml_file=toml_path)
            return (init_settings, normalized_env, toml_source)
        return (init_settings, normalized_env)


def get_settings() -> Settings:
    """Build a fresh :class:`Settings` from the current environment + TOML.

    Intentionally uncached: reading is cheap and callers (and tests that
    ``monkeypatch`` env vars) expect live reads, matching the pre-schema
    functions this replaces.
    """
    return Settings()


def storage_config_problems(settings: Settings) -> List[str]:
    """Return human-readable problems with the storage config (empty list = OK).

    Validates that the selected provider has the fields it needs. Data emptiness
    is deliberately NOT checked here — a fresh environment may legitimately boot
    with an empty container (that is a deploy-gate concern, a startup warning at
    most), so this only covers configuration validity.
    """
    problems: List[str] = []
    if settings.storage_provider == "azure_blob":
        required = {
            "AZURE_STORAGE_ACCOUNT": settings.azure_storage_account,
            "AZURE_STORAGE_CONTAINER": settings.azure_storage_container,
            "AZURE_STORAGE_KEY": settings.azure_storage_key,
        }
        for name, value in required.items():
            if not value:
                problems.append(f"{name} is required when STORAGE_PROVIDER=azure_blob")
    elif settings.storage_provider not in ("local", "aws_s3", "gcs"):
        problems.append(f"Unknown STORAGE_PROVIDER {settings.storage_provider!r}")
    return problems


def enforce_startup_config(settings: Optional[Settings] = None) -> List[str]:
    """Validate configuration at startup with an environment-dependent posture.

    Hard-fails (raises ``RuntimeError``) in ``production`` on any problem so a
    mis-configured release never boots; warns and degrades in every other
    environment. Returns the list of problems (empty when clean). Never inspects
    data counts — see :func:`storage_config_problems`.
    """
    settings = settings or get_settings()
    problems = storage_config_problems(settings)
    if not problems:
        return problems
    detail = "; ".join(problems)
    if settings.environment == "production":
        raise RuntimeError(f"Invalid production configuration: {detail}")
    logger.warning(
        "Configuration problems (continuing in %s, degraded): %s",
        settings.environment,
        detail,
    )
    return problems
