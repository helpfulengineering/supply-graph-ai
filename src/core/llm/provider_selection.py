"""
LLM Provider Selection Utility for the Open Matching Engine.

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


class ProviderSelectionStrategy(Enum):
    """Strategy for provider selection"""

    ENV_VAR = "env_var"
    CLI_FLAG = "cli_flag"
    DEFAULT = "default"
    AUTO_DETECT = "auto_detect"


class LLMProviderSelector:
    """
    Handles LLM provider selection with multiple fallback strategies.

    Selection priority:
    1. Command line flag (highest priority)
    2. Environment variable
    3. Auto-detection based on available API keys
    4. Default fallback (lowest priority)
    """

    # Default provider preferences (in order of preference)
    DEFAULT_PROVIDER_PREFERENCES = [
        LLMProviderType.ANTHROPIC,  # Most reliable for our use case
        LLMProviderType.OPENAI,  # Widely available
        LLMProviderType.LOCAL,  # Free local option
    ]

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

    def select_provider(
        self,
        cli_provider: Optional[str] = None,
        cli_model: Optional[str] = None,
        env_provider: Optional[str] = None,
        env_model: Optional[str] = None,
        auto_detect: bool = True,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """
        Select the best available LLM provider and model.

        Args:
            cli_provider: Provider specified via command line flag
            cli_model: Model specified via command line flag
            env_provider: Provider specified via environment variable
            env_model: Model specified via environment variable
            auto_detect: Whether to auto-detect available providers
            verbose: Whether to log selection details

        Returns:
            Dict containing provider, model, strategy, and metadata
        """
        selection_result = {
            "provider": None,
            "model": None,
            "strategy": None,
            "reason": None,
            "available_providers": [],
            "warnings": [],
            "errors": [],
        }

        # Get available providers
        available_providers = self._get_available_providers()
        selection_result["available_providers"] = [p.value for p in available_providers]

        if not available_providers:
            selection_result["errors"].append("No LLM providers are available")
            if verbose:
                logger.error(
                    "❌ No LLM providers are available. Please check your configuration."
                )
            return selection_result

        # Strategy 1: Command line flag (highest priority)
        if cli_provider:
            try:
                provider_type = LLMProviderType(cli_provider)
                if provider_type in available_providers:
                    model = cli_model or self.DEFAULT_MODELS.get(provider_type)
                    selection_result.update(
                        {
                            "provider": provider_type,
                            "model": model,
                            "strategy": ProviderSelectionStrategy.CLI_FLAG,
                            "reason": f"Command line flag specified: {cli_provider}",
                        }
                    )
                    if verbose:
                        logger.info(
                            f"🎯 Using LLM provider '{provider_type.value}' (CLI flag: --provider {cli_provider})"
                        )
                        logger.info(f"🤖 Using model '{model}'")
                    return selection_result
                else:
                    selection_result["warnings"].append(
                        f"CLI provider '{cli_provider}' not available"
                    )
                    if verbose:
                        logger.warning(
                            f"⚠️  CLI provider '{cli_provider}' not available, falling back to other options"
                        )
            except ValueError:
                selection_result["warnings"].append(
                    f"Invalid CLI provider '{cli_provider}'"
                )
                if verbose:
                    logger.warning(
                        f"⚠️  Invalid CLI provider '{cli_provider}', falling back to other options"
                    )

        # Strategy 2: Environment variable
        if env_provider:
            try:
                provider_type = LLMProviderType(env_provider)
                if provider_type in available_providers:
                    model = (
                        env_model or cli_model or self.DEFAULT_MODELS.get(provider_type)
                    )
                    selection_result.update(
                        {
                            "provider": provider_type,
                            "model": model,
                            "strategy": ProviderSelectionStrategy.ENV_VAR,
                            "reason": f"Environment variable specified: {env_provider}",
                        }
                    )
                    if verbose:
                        logger.info(
                            f"🎯 Using LLM provider '{provider_type.value}' (ENV: LLM_PROVIDER={env_provider})"
                        )
                        logger.info(f"🤖 Using model '{model}'")
                    return selection_result
                else:
                    selection_result["warnings"].append(
                        f"ENV provider '{env_provider}' not available"
                    )
                    if verbose:
                        logger.warning(
                            f"⚠️  ENV provider '{env_provider}' not available, falling back to other options"
                        )
            except ValueError:
                selection_result["warnings"].append(
                    f"Invalid ENV provider '{env_provider}'"
                )
                if verbose:
                    logger.warning(
                        f"⚠️  Invalid ENV provider '{env_provider}', falling back to other options"
                    )

        # Strategy 3: Auto-detection (if enabled)
        if auto_detect:
            best_provider = self._auto_detect_best_provider(available_providers)
            if best_provider:
                model = cli_model or env_model or self.DEFAULT_MODELS.get(best_provider)
                selection_result.update(
                    {
                        "provider": best_provider,
                        "model": model,
                        "strategy": ProviderSelectionStrategy.AUTO_DETECT,
                        "reason": f"Auto-detected best available provider: {best_provider.value}",
                    }
                )
                if verbose:
                    logger.info(
                        f"🎯 Auto-detected LLM provider '{best_provider.value}' (best available)"
                    )
                    logger.info(f"🤖 Using model '{model}'")
                return selection_result

        # Strategy 4: Default fallback
        default_provider = self._get_default_provider(available_providers)
        if default_provider:
            model = cli_model or env_model or self.DEFAULT_MODELS.get(default_provider)
            selection_result.update(
                {
                    "provider": default_provider,
                    "model": model,
                    "strategy": ProviderSelectionStrategy.DEFAULT,
                    "reason": f"Using default provider: {default_provider.value}",
                }
            )
            if verbose:
                logger.info(f"🎯 Using default LLM provider '{default_provider.value}'")
                logger.info(f"🤖 Using model '{model}'")
            return selection_result

        # If we get here, something went wrong
        selection_result["errors"].append("Failed to select any provider")
        if verbose:
            logger.error("❌ Failed to select any LLM provider")

        return selection_result

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
        """Check if Ollama is available locally."""
        try:
            import asyncio

            import httpx

            async def check_ollama():
                try:
                    async with httpx.AsyncClient(timeout=2.0) as client:
                        response = await client.get("http://localhost:11434/api/tags")
                        return response.status_code == 200
                except:
                    return False

            # Run the async check
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, we can't use asyncio.run
                # For now, assume Ollama is available if we can't check
                return True
            else:
                return asyncio.run(check_ollama())
        except:
            return False

    def _auto_detect_best_provider(
        self, available_providers: List[LLMProviderType]
    ) -> Optional[LLMProviderType]:
        """Auto-detect the best provider from available options."""
        # Use our preference order
        for preferred in self.DEFAULT_PROVIDER_PREFERENCES:
            if preferred in available_providers:
                return preferred

        # If none of our preferences are available, return the first available
        return available_providers[0] if available_providers else None

    def _get_default_provider(
        self, available_providers: List[LLMProviderType]
    ) -> Optional[LLMProviderType]:
        """Get the default provider from available options."""
        return self._auto_detect_best_provider(available_providers)

    def create_llm_service(
        self,
        cli_provider: Optional[str] = None,
        cli_model: Optional[str] = None,
        verbose: bool = True,
    ) -> LLMService:
        """
        Create an LLM service with the best available provider.

        Args:
            cli_provider: Provider specified via command line flag
            cli_model: Model specified via command line flag
            verbose: Whether to log selection details

        Returns:
            Configured LLMService instance
        """
        # Get environment variables
        env_provider = os.getenv("LLM_PROVIDER")
        env_model = os.getenv("LLM_MODEL")

        # Select provider
        selection = self.select_provider(
            cli_provider=cli_provider,
            cli_model=cli_model,
            env_provider=env_provider,
            env_model=env_model,
            verbose=verbose,
        )

        if not selection["provider"]:
            raise RuntimeError(f"Failed to select LLM provider: {selection['errors']}")

        # Create service configuration
        service_config = LLMServiceConfig(
            default_provider=selection["provider"], default_model=selection["model"]
        )

        # Create and return service
        service = LLMService(service_config)

        if verbose:
            logger.info(
                f"✅ LLM service created with provider '{selection['provider'].value}' and model '{selection['model']}'"
            )

        return service

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


def select_llm_provider(
    cli_provider: Optional[str] = None,
    cli_model: Optional[str] = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Select the best available LLM provider.

    Args:
        cli_provider: Provider specified via command line flag
        cli_model: Model specified via command line flag
        verbose: Whether to log selection details

    Returns:
        Selection result dictionary
    """
    return get_provider_selector().select_provider(
        cli_provider=cli_provider, cli_model=cli_model, verbose=verbose
    )


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
    service = get_provider_selector().create_llm_service(
        cli_provider=cli_provider, cli_model=cli_model, verbose=verbose
    )

    # Initialize the service
    await service.initialize()

    return service
