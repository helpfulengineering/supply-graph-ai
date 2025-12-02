import logging
import os
from typing import Dict, Optional

from dotenv import load_dotenv

from src.core.storage.base import StorageConfig

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class StorageConfigError(Exception):
    """Base exception for storage configuration errors"""

    pass


class MissingCredentialsError(StorageConfigError):
    """Raised when required credentials are missing"""

    pass


def get_azure_credentials() -> Dict[str, str]:
    """Get Azure Blob Storage credentials from environment variables"""
    account_name = os.getenv("AZURE_STORAGE_ACCOUNT")
    account_key = os.getenv("AZURE_STORAGE_KEY")

    if not account_name or not account_key:
        raise MissingCredentialsError(
            "Azure storage credentials not found. "
            "Please set AZURE_STORAGE_ACCOUNT and AZURE_STORAGE_KEY environment variables."
        )

    return {"account_name": account_name, "account_key": account_key}


def get_aws_credentials() -> Dict[str, str]:
    """Get AWS S3 credentials from environment variables"""
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

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
    project_id = os.getenv("GCP_PROJECT_ID")
    credentials_json = os.getenv("GCP_CREDENTIALS_JSON")
    credentials_path = os.getenv("GCP_CREDENTIALS_PATH")

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
            bucket_name = os.getenv("AZURE_STORAGE_CONTAINER")
    elif provider == "aws_s3":
        credentials = get_aws_credentials()
        if not bucket_name:
            bucket_name = os.getenv("AWS_S3_BUCKET")
    elif provider == "gcs":
        credentials = get_gcp_credentials()
        if not bucket_name:
            bucket_name = os.getenv("GCP_STORAGE_BUCKET")
    elif provider == "local":
        if not bucket_name:
            bucket_name = os.getenv("LOCAL_STORAGE_PATH", "storage")
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
    provider = os.getenv("STORAGE_PROVIDER", "local")
    return create_storage_config(provider)
