"""Secrets Manager abstraction for cloud deployment

This module provides a unified interface for retrieving secrets from various
cloud secrets managers (AWS Secrets Manager, GCP Secret Manager, Azure Key Vault)
with fallback to environment variables for local development and Cloud Run/ECS.
"""

import logging
import os
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SecretsProvider(Enum):
    """Supported secrets providers"""

    ENV = "env"  # Environment variables (default)
    AWS = "aws"  # AWS Secrets Manager
    GCP = "gcp"  # GCP Secret Manager
    AZURE = "azure"  # Azure Key Vault
    NONE = "none"  # No secrets manager (use env vars only)


class SecretsManager:
    """Unified secrets manager interface"""

    def __init__(self, provider: Optional[SecretsProvider] = None):
        """Initialize secrets manager

        Args:
            provider: Secrets provider to use. If None, auto-detect from environment.
        """
        self.provider = provider or self._detect_provider()
        self._cache: Dict[str, str] = {}
        self._initialized = False

        if self.provider != SecretsProvider.ENV:
            try:
                self._initialize_provider()
            except Exception as e:
                logger.warning(
                    f"Failed to initialize {self.provider.value} secrets manager: {e}. "
                    "Falling back to environment variables."
                )
                self.provider = SecretsProvider.ENV

    def _detect_provider(self) -> SecretsProvider:
        """Auto-detect secrets provider from environment"""
        # Check explicit configuration
        provider_env = os.getenv("SECRETS_PROVIDER", "").lower()
        if provider_env:
            try:
                return SecretsProvider(provider_env)
            except ValueError:
                logger.warning(f"Unknown SECRETS_PROVIDER: {provider_env}. Using ENV.")

        # Auto-detect from cloud environment
        if os.getenv("AWS_EXECUTION_ENV") or os.getenv("ECS_CONTAINER_METADATA_URI"):
            # AWS environment - check if AWS credentials are available
            if os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_SECRET_ACCESS_KEY"):
                return SecretsProvider.AWS

        if os.getenv("K_SERVICE") or os.getenv("GOOGLE_CLOUD_PROJECT"):
            # GCP environment
            return SecretsProvider.GCP

        if os.getenv("WEBSITE_INSTANCE_ID") or os.getenv("AZURE_STORAGE_ACCOUNT"):
            # Azure environment
            return SecretsProvider.AZURE

        # Default to environment variables
        return SecretsProvider.ENV

    def _initialize_provider(self):
        """Initialize the secrets provider client"""
        if self.provider == SecretsProvider.AWS:
            self._init_aws()
        elif self.provider == SecretsProvider.GCP:
            self._init_gcp()
        elif self.provider == SecretsProvider.AZURE:
            self._init_azure()

        self._initialized = True

    def _init_aws(self):
        """Initialize AWS Secrets Manager client"""
        try:
            import boto3

            region = os.getenv(
                "AWS_DEFAULT_REGION", os.getenv("AWS_REGION", "us-east-1")
            )
            self._client = boto3.client("secretsmanager", region_name=region)
            logger.info("Initialized AWS Secrets Manager client")
        except ImportError:
            raise ImportError("boto3 is required for AWS Secrets Manager")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize AWS Secrets Manager: {e}")

    def _init_gcp(self):
        """Initialize GCP Secret Manager client"""
        try:
            from google.cloud import secretmanager

            project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv(
                "GCP_PROJECT_ID"
            )
            if not project_id:
                raise ValueError(
                    "GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID must be set for GCP Secret Manager"
                )
            self._client = secretmanager.SecretManagerServiceClient()
            self._project_id = project_id
            logger.info(
                f"Initialized GCP Secret Manager client for project {project_id}"
            )
        except ImportError:
            raise ImportError(
                "google-cloud-secret-manager is required for GCP Secret Manager"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize GCP Secret Manager: {e}")

    def _init_azure(self):
        """Initialize Azure Key Vault client"""
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            vault_url = os.getenv("AZURE_KEY_VAULT_URL")
            if not vault_url:
                raise ValueError("AZURE_KEY_VAULT_URL must be set for Azure Key Vault")

            credential = DefaultAzureCredential()
            self._client = SecretClient(vault_url=vault_url, credential=credential)
            logger.info(f"Initialized Azure Key Vault client for {vault_url}")
        except ImportError:
            raise ImportError(
                "azure-keyvault-secrets and azure-identity are required for Azure Key Vault"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Azure Key Vault: {e}")

    def get_secret(
        self, secret_name: str, default: Optional[str] = None
    ) -> Optional[str]:
        """Get a secret value

        Args:
            secret_name: Name of the secret (environment variable name or secret name)
            default: Default value if secret is not found

        Returns:
            Secret value or default
        """
        # Check cache first
        if secret_name in self._cache:
            return self._cache[secret_name]

        # Try secrets manager first (if not using ENV provider)
        if self.provider != SecretsProvider.ENV and self._initialized:
            try:
                value = self._get_from_provider(secret_name)
                if value:
                    self._cache[secret_name] = value
                    return value
            except Exception as e:
                logger.debug(
                    f"Failed to get secret {secret_name} from {self.provider.value}: {e}"
                )

        # Fall back to environment variable
        value = os.getenv(secret_name, default)
        if value:
            self._cache[secret_name] = value

        return value

    def _get_from_provider(self, secret_name: str) -> Optional[str]:
        """Get secret from the configured provider"""
        if self.provider == SecretsProvider.AWS:
            return self._get_from_aws(secret_name)
        elif self.provider == SecretsProvider.GCP:
            return self._get_from_gcp(secret_name)
        elif self.provider == SecretsProvider.AZURE:
            return self._get_from_azure(secret_name)
        return None

    def _get_from_aws(self, secret_name: str) -> Optional[str]:
        """Get secret from AWS Secrets Manager"""
        try:
            # AWS Secrets Manager uses secret names, not environment variable names
            # Try secret name as-is first, then try with common prefixes
            secret_id = secret_name

            # If secret_name looks like an env var (e.g., OPENAI_API_KEY),
            # try converting to secret name format
            if "_" in secret_name:
                # Try lowercase with hyphens
                secret_id = secret_name.lower().replace("_", "-")

            response = self._client.get_secret_value(SecretId=secret_id)

            # AWS Secrets Manager can store JSON strings
            secret_string = response.get("SecretString", "")
            try:
                import json

                secret_dict = json.loads(secret_string)
                # If it's a dict, try to get the value by the original key
                if isinstance(secret_dict, dict):
                    return secret_dict.get(secret_name) or secret_dict.get(secret_id)
            except (json.JSONDecodeError, TypeError):
                pass

            return secret_string
        except self._client.exceptions.ResourceNotFoundException:
            logger.debug(f"Secret {secret_id} not found in AWS Secrets Manager")
            return None
        except Exception as e:
            logger.warning(f"Error retrieving secret {secret_id} from AWS: {e}")
            return None

    def _get_from_gcp(self, secret_name: str) -> Optional[str]:
        """Get secret from GCP Secret Manager"""
        try:
            # GCP Secret Manager uses secret names
            # Convert env var name to secret name (e.g., OPENAI_API_KEY -> openai-api-key)
            secret_id = secret_name.lower().replace("_", "-")

            name = f"projects/{self._project_id}/secrets/{secret_id}/versions/latest"
            response = self._client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            # Check if it's a "not found" error
            if "not found" in str(e).lower() or "404" in str(e):
                logger.debug(f"Secret {secret_id} not found in GCP Secret Manager")
            else:
                logger.warning(f"Error retrieving secret {secret_id} from GCP: {e}")
            return None

    def _get_from_azure(self, secret_name: str) -> Optional[str]:
        """Get secret from Azure Key Vault"""
        try:
            # Azure Key Vault uses secret names
            # Convert env var name to secret name (e.g., OPENAI_API_KEY -> openai-api-key)
            secret_id = secret_name.lower().replace("_", "-")

            secret = self._client.get_secret(secret_id)
            return secret.value
        except Exception as e:
            # Check if it's a "not found" error
            if "not found" in str(e).lower() or "404" in str(e):
                logger.debug(f"Secret {secret_id} not found in Azure Key Vault")
            else:
                logger.warning(f"Error retrieving secret {secret_id} from Azure: {e}")
            return None

    def get_secrets_batch(self, secret_names: list[str]) -> Dict[str, Optional[str]]:
        """Get multiple secrets at once

        Args:
            secret_names: List of secret names to retrieve

        Returns:
            Dictionary mapping secret names to values
        """
        return {name: self.get_secret(name) for name in secret_names}


# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager instance"""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


def get_secret(secret_name: str, default: Optional[str] = None) -> Optional[str]:
    """Convenience function to get a secret

    Args:
        secret_name: Name of the secret
        default: Default value if not found

    Returns:
        Secret value or default
    """
    return get_secrets_manager().get_secret(secret_name, default)
