"""
LLM Provider Selection Utility for the Open Hardware Manager.

This module provides an LLM provider selection system that supports:
- Environment variable configuration
- Command line flag overrides
- Sensible defaults with clear logging
- Provider availability checking
"""

import logging
import os
from enum import Enum
from typing import Any, Dict, List, Optional

from .providers.base import LLMProviderType
from .service import LLMService, LLMServiceConfig

logger = logging.getLogger(__name__)


class LLMProviderSelector:
    """
    Handles LLM provider selection with multiple fallback strategies.

    Selection priority:
    1. Command line flag (highest priority)
    2. Environment variable
    3. Auto-detection based on available API keys
    4. Default fallback (lowest priority)
    """

    # Provider-specific environment variable names
    PROVIDER_ENV_VARS = {
        LLMProviderType.ANTHROPIC: "ANTHROPIC_API_KEY",
        LLMProviderType.OPENAI: "OPENAI_API_KEY",
        LLMProviderType.LOCAL: "OLLAMA_BASE_URL",  # Optional for local
        LLMProviderType.AZURE_OPENAI: "AZURE_OPENAI_API_KEY",
        LLMProviderType.AWS_BEDROCK: "AWS_BEDROCK_API_KEY",  # Optional, can use AWS credentials
        LLMProviderType.GOOGLE: "GOOGLE_APPLICATION_CREDENTIALS",  # Service account JSON path
    }

    # Default models for each provider
    DEFAULT_MODELS = {
        LLMProviderType.ANTHROPIC: "claude-sonnet-4-5-20250929",
        LLMProviderType.OPENAI: "gpt-3.5-turbo",
        LLMProviderType.LOCAL: "llama3.1:8b",
        LLMProviderType.AZURE_OPENAI: "gpt-35-turbo",
        LLMProviderType.AWS_BEDROCK: "anthropic.claude-3-5-sonnet-20241022-v2:0",
        LLMProviderType.GOOGLE: "gemini-1.5-pro",
    }

    def __init__(self):
        """Initialize the provider selector."""
        self._cached_available_providers: Optional[List[LLMProviderType]] = None

    def invalidate_availability_cache(self) -> None:
        """Drop cached provider availability (call after credentials change)."""
        self._cached_available_providers = None

    def _get_available_providers(self) -> List[LLMProviderType]:
        """Get list of available providers based on API keys and configuration."""
        if self._cached_available_providers is not None:
            return self._cached_available_providers

        available = []

        for provider_type in LLMProviderType:
            if self._is_provider_available(provider_type):
                available.append(provider_type)

        self._cached_available_providers = available
        return available

    def _is_provider_available(self, provider_type: LLMProviderType) -> bool:
        """Check if a provider is available (has API key or is local)."""
        if provider_type == LLMProviderType.LOCAL:
            # For local providers, check if Ollama is running
            return self._is_ollama_available()

        if provider_type == LLMProviderType.AZURE_OPENAI:
            # Azure OpenAI requires API key, endpoint, and deployment ID
            return (
                os.getenv("AZURE_OPENAI_API_KEY") is not None
                and os.getenv("AZURE_OPENAI_ENDPOINT") is not None
                and os.getenv("AZURE_OPENAI_DEPLOYMENT_ID") is not None
            )

        if provider_type == LLMProviderType.AWS_BEDROCK:
            # AWS Bedrock can use API key or AWS credentials (from environment/IAM role)
            # Check for API key first, then check for AWS credentials
            if os.getenv("AWS_BEDROCK_API_KEY") is not None:
                return True
            # Check for AWS credentials (access key or IAM role)
            if os.getenv("AWS_ACCESS_KEY_ID") is not None:
                return True
            # If running on AWS, might have IAM role credentials
            # For simplicity, we'll check if boto3 can find credentials
            try:
                import boto3

                session = boto3.Session()
                credentials = session.get_credentials()
                return credentials is not None
            except ImportError:
                return False

        if provider_type == LLMProviderType.GOOGLE:
            # Google Vertex AI requires service account credentials
            # Check for explicit credentials path
            if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") is not None:
                return os.path.exists(os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""))
            # Check for project ID (required)
            if os.getenv("GOOGLE_CLOUD_PROJECT") is not None:
                # Try to use default credentials (from gcloud or metadata server)
                try:
                    from google.auth import default as google_auth_default

                    credentials, _ = google_auth_default()
                    return credentials is not None
                except Exception:
                    return False
            return False

        # For other cloud providers, check for API key
        env_var = self.PROVIDER_ENV_VARS.get(provider_type)
        if env_var:
            return os.getenv(env_var) is not None

        return False

    def _is_ollama_available(self) -> bool:
        """Whether ollama has been opted into.

        Deliberately NOT a network probe. It used to open a connection to a
        hardcoded localhost address and, when it could not check — which is
        always, from inside a running event loop — report available anyway. So
        every node claimed a local model it did not have.

        Opt-in is the same test generation uses: the base URL is set, or ollama
        is named as the provider. One question, one answer, both paths.
        """
        from .availability import OLLAMA_PROVIDER, _configured_ollama_url

        if _configured_ollama_url():
            return True
        from src.config.schema import get_settings

        return get_settings().llm_default_provider == OLLAMA_PROVIDER

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about all providers and their availability."""
        info = {
            "available_providers": [],
            "unavailable_providers": [],
            "provider_details": {},
        }

        for provider_type in LLMProviderType:
            is_available = self._is_provider_available(provider_type)
            provider_info = {
                "type": provider_type.value,
                "available": is_available,
                "default_model": self.DEFAULT_MODELS.get(provider_type),
                "env_var": self.PROVIDER_ENV_VARS.get(provider_type),
                "has_api_key": (
                    os.getenv(self.PROVIDER_ENV_VARS.get(provider_type)) is not None
                    if self.PROVIDER_ENV_VARS.get(provider_type)
                    else False
                ),
            }

            info["provider_details"][provider_type.value] = provider_info

            if is_available:
                info["available_providers"].append(provider_type.value)
            else:
                info["unavailable_providers"].append(provider_type.value)

        return info


# Global provider selector instance
_provider_selector: Optional[LLMProviderSelector] = None


def get_provider_selector() -> LLMProviderSelector:
    """Get the global provider selector instance."""
    global _provider_selector
    if _provider_selector is None:
        _provider_selector = LLMProviderSelector()
    return _provider_selector


def default_model_for(provider_name: Optional[str]) -> Optional[str]:
    """Return the default model for a provider name string.
    Centralized helper to avoid scattered hard-coding.
    """
    if not provider_name:
        return None
    try:
        provider_type = LLMProviderType(provider_name)
    except ValueError:
        return None
    selector = get_provider_selector()
    return selector.DEFAULT_MODELS.get(provider_type)


async def create_llm_service_with_selection(
    cli_provider: Optional[str] = None,
    cli_model: Optional[str] = None,
    verbose: bool = True,
) -> LLMService:
    """
    Create an LLM service with automatic provider selection.

    Args:
        cli_provider: Provider specified via command line flag
        cli_model: Model specified via command line flag
        verbose: Whether to log selection details

    Returns:
        Configured LLMService instance
    """
    from .availability import LLMUnavailableReason, resolve_llm_availability

    # ONE decision, shared with generation. This used to select independently
    # from process environment variables only, so a credential stored through
    # Settings reached generation but was invisible here — `ohm llm` reported no
    # provider on a node that was happily generating with one.
    availability = await resolve_llm_availability(preferred_provider=cli_provider)

    if not availability.available:
        raise RuntimeError(_no_provider_message(availability.reason, cli_provider))

    provider = LLMProviderType(availability.provider)
    model = cli_model or default_model_for(availability.provider)

    if verbose:
        logger.info(
            "Using LLM provider '%s' (%s) with model '%s'",
            availability.provider,
            availability.source,
            model,
        )

    # NB the name comes FIRST. Passing the config positionally leaves `config`
    # None and silently falls back to defaults — which is what the previous
    # implementation did, so `ohm llm --provider openai` has always quietly run
    # Anthropic on the default model.
    service = LLMService(
        "LLMProviderSelection",
        LLMServiceConfig(default_provider=provider, default_model=model),
    )
    await service.initialize()
    return service


def _no_provider_message(reason: Optional[str], requested: Optional[str]) -> str:
    """Say what to do about it, not just that it happened."""
    from .availability import LLMUnavailableReason

    if reason == LLMUnavailableReason.DISABLED:
        return "LLM use is switched off (LLM_ENABLED=false)."
    if requested:
        return (
            f"No credential configured for provider {requested!r}. Add one in "
            f"Settings → LLM providers, or set its API key in the environment."
        )
    return (
        "No LLM provider is configured. Add a credential in Settings → LLM "
        "providers, set a provider API key in the environment, or run a local "
        "model with LLM_DEFAULT_PROVIDER=local."
    )
