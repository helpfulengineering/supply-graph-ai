"""Secrets the Celery worker shares with the API container app.

Container App secrets are per-app, so the worker needs its own copy of the
storage key and the git access tokens. Rather than requiring them to be set by
hand — which drifts silently the first time one is rotated and the other is
forgotten — the worker deploy MIRRORS them from the API app on every deploy.
The API app is the single source, so the copies cannot diverge.

Values are read and written by the deploy identity, which already holds the
rights to do both; they are never logged and never checked in.
"""

from __future__ import annotations

from typing import Dict

# Container env var -> the Container App secret holding its value. The same
# names are used on both apps so the two are comparable secret-for-secret.
#
# NB `gihub-token` is missing a 't'. That is the real name of the live secret;
# correcting it is a separate change that must rename on both apps at once.
MIRRORED_SECRET_ENV_REFS: Dict[str, str] = {
    "AZURE_STORAGE_KEY": "azure-storage-key",
    "GITHUB_ACCESS_TOKEN": "gihub-token",
    "GITLAB_ACCESS_TOKEN": "gitlab-token",
    # Required by ANY app that imports src.config with ENVIRONMENT=production —
    # settings.py builds LLMConfigManager at import time, and CredentialManager
    # raises without these. That is true whether or not the app ever touches an
    # LLM, so the worker needs them even with LLM generation out of scope.
    # Omitting them crash-looped the production worker at startup; a `staging`
    # environment cannot catch it, because the guard only fires when ENVIRONMENT
    # is literally "production".
    "LLM_ENCRYPTION_SALT": "llm-encryption-salt",
    "LLM_ENCRYPTION_PASSWORD": "llm-encryption-password",
}

# The API additionally serves authenticated routes; a worker consumes jobs and
# never authenticates a caller, so it has no use for these.
API_ONLY_SECRET_ENV_REFS: Dict[str, str] = {
    "API_KEYS": "api-key",
}


def shared_secret_env_refs(*, include_api_keys: bool = False) -> Dict[str, str]:
    """Env var -> secret name for the apps that share these credentials."""
    refs = dict(MIRRORED_SECRET_ENV_REFS)
    if include_api_keys:
        refs.update(API_ONLY_SECRET_ENV_REFS)
    return refs


def mirrored_secret_names(*, include_api_keys: bool = False) -> list[str]:
    """Secret names to copy from the source app onto the target app."""
    return sorted(
        set(shared_secret_env_refs(include_api_keys=include_api_keys).values())
    )


def mirrored_secret_env_vars(*, include_api_keys: bool = False) -> Dict[str, str]:
    """Env vars referencing the mirrored secrets, never their values.

    The worker reads and writes the same blob storage as the API
    (``AZURE_STORAGE_KEY``) and does the repository cloning itself — without the
    git tokens every generation hits anonymous rate limits, which surfaces to
    users as a rate-limit error with no obvious cause.
    """
    return {
        env_var: f"secretref:{secret}"
        for env_var, secret in shared_secret_env_refs(
            include_api_keys=include_api_keys
        ).items()
    }
