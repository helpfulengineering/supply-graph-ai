import asyncio
import logging
from typing import Any, Dict, List, Optional, Type

from src.core.utils.secrets_manager import get_secrets_manager
from src.core.integration.config.config import IntegrationConfig
from src.core.integration.models.base import (
    IntegrationCategory,
    IntegrationRequest,
    IntegrationResponse,
    ProviderStatus,
)
from src.core.integration.providers.base import BaseIntegrationProvider

logger = logging.getLogger(__name__)


class IntegrationManager:
    """
    Singleton manager for all external integrations.

    Handles provider registration, configuration loading, and request routing.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IntegrationManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.providers: Dict[str, BaseIntegrationProvider] = {}
        self.provider_classes: Dict[str, Type[BaseIntegrationProvider]] = {}
        self.config: Optional[IntegrationConfig] = None
        self._secrets_manager = get_secrets_manager()
        self._lock = asyncio.Lock()
        # Do not set _initialized = True here, as it blocks initialize() from running
        logger.info("IntegrationManager instantiated")

    @classmethod
    def get_instance(cls) -> "IntegrationManager":
        """Get the singleton instance."""
        return cls()

    def register_provider_class(
        self, provider_type: str, provider_class: Type[BaseIntegrationProvider]
    ):
        """Register a provider class."""
        self.provider_classes[provider_type] = provider_class
        logger.info(f"Registered provider class: {provider_type}")

    async def initialize(self, config_path: str = "config/integration_config.json"):
        """Initialize the manager with configuration."""
        if self._initialized:
            return

        async with self._lock:
            # Double-check inside lock
            if self._initialized:
                return

            import json
            import os

            # Load configuration
            try:
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        config_data = json.load(f)
                    self.config = IntegrationConfig(**config_data)
                else:
                    logger.warning(
                        f"Configuration file {config_path} not found. Using default config."
                    )
                    self.config = IntegrationConfig()
            except Exception as e:
                logger.error(f"Failed to load configuration: {e}")
                self.config = IntegrationConfig()

            # Register default provider classes
        from .providers.github import GitHubProvider
        from .providers.gitlab import GitLabProvider

        self.register_provider_class("github", GitHubProvider)
        self.register_provider_class("gitlab", GitLabProvider)

        # Initialize providers from config
        if self.config and self.config.providers:
            for provider_name, provider_config in self.config.providers.items():
                try:
                    provider_type = provider_config.get("provider_type")
                    if provider_type in self.provider_classes:
                        # Inject secrets if needed
                        if provider_config.get("use_secrets", False):
                            secret_key = provider_config.get("secret_key_env")
                            if secret_key:
                                secret_value = self._secrets_manager.get_secret(
                                    secret_key
                                )
                                if secret_value:
                                    provider_config["api_key"] = secret_value

                        provider_class = self.provider_classes[provider_type]
                        provider_instance = provider_class(provider_config)
                        await provider_instance.connect()
                        self.providers[provider_name] = provider_instance
                        logger.info(f"Initialized provider: {provider_name}")
                    else:
                        logger.warning(
                            f"Provider type {provider_type} not registered. Skipping {provider_name}."
                        )
                except Exception as e:
                    logger.error(f"Failed to initialize provider {provider_name}: {e}")

        self._initialized = True
        logger.info("IntegrationManager initialization complete")

    async def get_provider(self, provider_name: str) -> Optional[BaseIntegrationProvider]:
        """Get a specific provider by name."""
        return self.providers.get(provider_name)

    async def get_providers_by_category(
        self, category: IntegrationCategory
    ) -> List[BaseIntegrationProvider]:
        """Get all providers for a specific category."""
        return [p for p in self.providers.values() if p.category == category]

    async def execute_request(
        self, provider_name: str, request: IntegrationRequest
    ) -> IntegrationResponse:
        """Execute a request against a specific provider."""
        provider = self.providers.get(provider_name)
        if not provider:
            return IntegrationResponse(
                success=False,
                data=None,
                error=f"Provider {provider_name} not found or not initialized",
            )

        try:
            return await provider.execute(request)
        except Exception as e:
            logger.error(f"Error executing request on {provider_name}: {e}")
            return IntegrationResponse(success=False, data=None, error=str(e))

    async def shutdown(self):
        """Shutdown all providers."""
        for name, provider in self.providers.items():
            try:
                await provider.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting provider {name}: {e}")
        self.providers.clear()
        logger.info("IntegrationManager shutdown complete")
