import logging
import os
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv

from src.core.storage.base import StorageConfig

logger = logging.getLogger(__name__)


def _find_project_env() -> Optional[Path]:
    """Find .env by walking up from this file (e.g. project root has .env)."""
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


# Load environment variables: prefer project root .env so storage config is correct
# regardless of process cwd (e.g. when running `ohm` from any directory).
_env_path = _find_project_env()
if _env_path:
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()


class StorageConfigError(Exception):
    """Base exception for storage configuration errors"""

    pass


class MissingCredentialsError(StorageConfigError):
    """Raised when required credentials are missing"""

    pass


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Read an env var and strip surrounding quotes.

    `docker run --env-file` passes values verbatim (quotes included), while
    python-dotenv (used by docker-compose and load_dotenv()) strips them.
    Stripping here makes both invocation styles produce identical credentials.
    """
    value = os.getenv(key, default)
    if value is None:
        return None
    stripped = value.strip().strip("\"'")
    return stripped if stripped else None


def get_azure_credentials() -> Dict[str, str]:
    """Get Azure Blob Storage credentials from the typed settings schema."""
    from src.config.schema import get_settings

    settings = get_settings()
    account_name = settings.azure_storage_account
    account_key = settings.azure_storage_key

    if not account_name or not account_key:
        raise MissingCredentialsError(
            "Azure storage credentials not found. "
            "Please set AZURE_STORAGE_ACCOUNT and AZURE_STORAGE_KEY environment variables."
        )

    return {"account_name": account_name, "account_key": account_key}


def get_aws_credentials() -> Dict[str, str]:
    """Get AWS S3 credentials from environment variables"""
    access_key = _env("AWS_ACCESS_KEY_ID")
    secret_key = _env("AWS_SECRET_ACCESS_KEY")
    region = _env("AWS_DEFAULT_REGION") or "us-east-1"

    if not access_key or not secret_key:
        raise MissingCredentialsError(
            "AWS credentials not found. "
            "Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
        )

    return {"access_key": access_key, "secret_key": secret_key, "region": region}


def get_gcp_credentials() -> Dict[str, str]:
    """Get Google Cloud Storage credentials from environment variables

    Supports multiple credential methods:
    1. GCP_CREDENTIALS_JSON: JSON string or file path to service account JSON
    2. GCP_CREDENTIALS_PATH: Explicit file path to service account JSON
    3. Application Default Credentials (if neither is set)

    GCP_PROJECT_ID is optional if it's in the credentials JSON.
    """
    project_id = _env("GCP_PROJECT_ID")
    credentials_json = _env("GCP_CREDENTIALS_JSON")
    credentials_path = _env("GCP_CREDENTIALS_PATH")

    # If credentials_path is explicitly set, use it
    if credentials_path:
        if not os.path.exists(credentials_path):
            raise MissingCredentialsError(
                f"GCP credentials file not found: {credentials_path}"
            )
        return {"project_id": project_id, "credentials_path": credentials_path}

    # If credentials_json is set, it could be a JSON string or file path
    if credentials_json:
        # Check if it's a file path
        if os.path.exists(credentials_json):
            return {"project_id": project_id, "credentials_path": credentials_json}
        else:
            # Treat as JSON string
            return {"project_id": project_id, "credentials_json": credentials_json}

    # If neither is set, use Application Default Credentials
    # This works if running on GCP or if gcloud auth application-default login was run
    logger.info(
        "No explicit GCP credentials found, will use Application Default Credentials"
    )
    return {"project_id": project_id}


def create_storage_config(
    provider: str,
    bucket_name: Optional[str] = None,
    region: Optional[str] = None,
    endpoint_url: Optional[str] = None,
    encryption: Optional[Dict[str, str]] = None,
) -> StorageConfig:
    """
    Create a StorageConfig object for the specified provider.

    Args:
        provider: The storage provider to use (azure_blob, aws_s3, gcs, local)
        bucket_name: Optional bucket/container name (defaults to provider-specific env var)
        region: Optional region for cloud providers
        endpoint_url: Optional custom endpoint URL
        encryption: Optional encryption settings

    Returns:
        StorageConfig object configured for the specified provider

    Raises:
        StorageConfigError: If configuration is invalid or credentials are missing
    """
    # Get provider-specific credentials
    credentials = {}
    if provider == "azure_blob":
        credentials = get_azure_credentials()
        if not bucket_name:
            from src.config.schema import get_settings

            bucket_name = get_settings().azure_storage_container
    elif provider == "aws_s3":
        credentials = get_aws_credentials()
        if not bucket_name:
            bucket_name = _env("AWS_S3_BUCKET")
    elif provider == "gcs":
        credentials = get_gcp_credentials()
        if not bucket_name:
            bucket_name = _env("GCP_STORAGE_BUCKET")
    elif provider == "local":
        if not bucket_name:
            bucket_name = _env("LOCAL_STORAGE_PATH") or "storage"
    else:
        raise StorageConfigError(f"Unsupported storage provider: {provider}")

    if not bucket_name:
        raise StorageConfigError(
            f"No bucket/container name specified for {provider}. "
            "Please provide bucket_name or set the appropriate environment variable."
        )

    # Create and return config
    return StorageConfig(
        provider=provider,
        bucket_name=bucket_name,
        region=region,
        credentials=credentials,
        endpoint_url=endpoint_url,
        encryption=encryption,
    )


def get_default_storage_config() -> StorageConfig:
    """
    Get the default storage configuration based on environment variables.

    The default provider is determined by the STORAGE_PROVIDER environment variable.
    If not set, it defaults to 'local'.

    Returns:
        StorageConfig object for the default provider

    Raises:
        StorageConfigError: If configuration is invalid or credentials are missing
    """
    from src.config.schema import get_settings

    provider = get_settings().storage_provider
    return create_storage_config(provider)


# ---------------------------------------------------------------------------
# OKW facility source (separate from blob storage provider)
# ---------------------------------------------------------------------------

_MOM_SPARQL_DEFAULT = "https://mapsofmaking.org/sparql/query"


def get_okw_source() -> str:
    """Return the OKW facility data source used during match requests.

    Set the ``OKW_SOURCE`` environment variable to switch at runtime.

    Values
    ------
    union (default — when ``OKW_SOURCE`` is unset)
        Match against **storage ∪ MoM**: the configured blob storage backend
        combined with the Maps of Making network. Chosen as the default so a
        match is not silently empty when no source has been selected.

    storage
        Load facilities from the configured blob storage backend
        (``STORAGE_PROVIDER``) only. Supports local, Azure Blob, AWS S3, GCS.

    mom
        Query the Maps of Making network only. No credentials required.
        Endpoint configured by ``MOM_SPARQL_ENDPOINT`` (see
        :func:`get_mom_config`).

    Returns
    -------
    str
        ``"union"``, ``"storage"``, or ``"mom"``. Unknown values fall back to
        ``"union"`` with a warning log.
    """
    from src.config.schema import get_settings

    return get_settings().okw_source_resolved


def resolve_effective_source(request_source: Optional[str] = None) -> str:
    """Combine the env-configured OKW source with an optional per-request override.

    Precedence: **the environment sets the universe; the request may narrow
    within it but never broaden it.**

    - env ``union`` → a request of ``"storage"``/``"mom"`` narrows the pool;
      otherwise the effective source stays ``union``.
    - env ``storage`` / ``mom`` are absolute — a request cannot broaden back to
      ``union`` or cross to the other source; the env value wins.

    Parameters
    ----------
    request_source
        Per-request override in OKW-source vocabulary (``"storage"``, ``"mom"``,
        ``"union"``, or ``None``). Unknown/empty values are treated as ``None``.

    Returns
    -------
    str
        The effective source: ``"union"``, ``"storage"``, or ``"mom"``.
    """
    env_source = get_okw_source()
    req = (request_source or "").strip().lower() or None
    if env_source != "union":
        return env_source
    if req in ("storage", "mom"):
        return req
    return "union"


def get_mom_config() -> Dict[str, str]:
    """Return Maps of Making (MoM) integration configuration.

    Environment variables
    ---------------------
    MOM_SPARQL_ENDPOINT
        Public SPARQL query endpoint for MoM's Oxigraph triplestore.
        Default: ``https://mapsofmaking.org/sparql/query``
        No authentication required.

    Returns
    -------
    dict
        ``{"endpoint": <sparql_url>}``
    """
    return {
        "endpoint": _env("MOM_SPARQL_ENDPOINT") or _MOM_SPARQL_DEFAULT,
    }
