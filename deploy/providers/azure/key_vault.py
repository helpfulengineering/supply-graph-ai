"""Container App secrets backed by Key Vault, resolved via managed identity.

Container App secrets are per-app, so every value two apps share exists twice.
The deploys mirror them so the copies cannot drift, but the API app is still the
origin: rotating a credential means editing it there and redeploying everything
downstream.

A Key Vault reference removes the copies entirely. Each secret exists once; both
apps hold a *pointer* to it, resolved at runtime through their managed identity.
Rotation becomes one edit with no deploy, and the mirroring — plus the drift
check that watched it — can retire.

Two constraints the platform imposes, both learned from its CLI rather than
assumed:

* A secret name carrying a Key Vault reference **cannot exceed 20 characters**.
  ``llm-encryption-password`` is 23, hence the rename recorded below.
* The reference is ``keyvaultref:<secret-uri>,identityref:<system|resource-id>``
  and the identity must already hold read access, or the app cannot start.
"""

from __future__ import annotations

from typing import Dict

# Longest permitted Container App secret name when it holds a Key Vault
# reference. Enforced by the platform; a longer name is rejected at deploy time.
MAX_SECRET_NAME_LENGTH = 20

# Env var -> Key Vault secret name. These are the values both apps need, each
# stored once. Key Vault secret names allow only alphanumerics and dashes.
#
# NB two names carry history:
#   * `gihub-token` is missing a 't' — the real name of the live secret. It is
#     renamed by a separate change, deliberately not bundled here.
#   * `llm-encrypt-password` was `llm-encryption-password` (23 chars), which
#     exceeds the limit above. The ENV VAR name is unchanged; only the secret's
#     name moves, so nothing in the application sees a difference.
KEY_VAULT_SECRET_REFS: Dict[str, str] = {
    "AZURE_STORAGE_KEY": "azure-storage-key",
    "GITHUB_ACCESS_TOKEN": "gihub-token",
    "GITLAB_ACCESS_TOKEN": "gitlab-token",
    "LLM_ENCRYPTION_SALT": "llm-encryption-salt",
    "LLM_ENCRYPTION_PASSWORD": "llm-encrypt-password",
    "API_KEYS": "api-key",
    "CACHE_REDIS_URL": "cache-redis-url",
    "JOB_BROKER_URL": "job-broker-url",
    "JOB_RESULT_BACKEND": "job-result-backend",
}

# The worker authenticates no callers, so it has no use for the API keys.
WORKER_EXCLUDED_SECRETS = {"API_KEYS"}


class SecretNameTooLongError(ValueError):
    """Raised when a secret name cannot carry a Key Vault reference."""


def secret_uri(vault_name: str, secret_name: str) -> str:
    """The Key Vault URI a Container App secret points at."""
    return f"https://{vault_name}.vault.azure.net/secrets/{secret_name}"


def key_vault_reference(vault_name: str, secret_name: str) -> str:
    """The ``keyvaultref:`` value for one secret, resolved by system identity.

    Raises:
        SecretNameTooLongError: if the name exceeds the platform limit. Failing
            here beats failing at deploy time with a platform error that does
            not say which name was at fault.
    """
    if len(secret_name) > MAX_SECRET_NAME_LENGTH:
        raise SecretNameTooLongError(
            f"Container App secret name {secret_name!r} is "
            f"{len(secret_name)} characters; Key Vault references allow at most "
            f"{MAX_SECRET_NAME_LENGTH}. Rename it in KEY_VAULT_SECRET_REFS."
        )
    return f"keyvaultref:{secret_uri(vault_name, secret_name)},identityref:system"


def secret_refs_for(*, worker: bool = False) -> Dict[str, str]:
    """Env var -> Key Vault secret name for one app's share of the secrets."""
    return {
        env_var: name
        for env_var, name in KEY_VAULT_SECRET_REFS.items()
        if not (worker and env_var in WORKER_EXCLUDED_SECRETS)
    }


def container_app_secrets(vault_name: str, *, worker: bool = False) -> Dict[str, str]:
    """Secret name -> ``keyvaultref:`` value, for ``az containerapp secret set``.

    Carries no secret values: every entry is a pointer, so this is safe to log.
    """
    return {
        name: key_vault_reference(vault_name, name)
        for name in secret_refs_for(worker=worker).values()
    }


def secret_env_vars(*, worker: bool = False) -> Dict[str, str]:
    """Env var -> ``secretref:`` pointer, unchanged in shape from before.

    The application sees no difference: it still reads an env var backed by a
    Container App secret. Only where that secret's *value* comes from changed.
    """
    return {
        env_var: f"secretref:{name}"
        for env_var, name in secret_refs_for(worker=worker).items()
    }
