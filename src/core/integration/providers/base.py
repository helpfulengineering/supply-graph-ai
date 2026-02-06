from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

from ..models.base import IntegrationCategory, IntegrationRequest, IntegrationResponse, ProviderStatus

logger = logging.getLogger(__name__)

class BaseIntegrationProvider(ABC):
    """
    Abstract base class for all integration providers.

    All providers must implement this interface to be registered with the IntegrationManager.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the provider with configuration.

        Args:
            config: Configuration dictionary for the provider
        """
        self.config = config
        self.category: IntegrationCategory = IntegrationCategory.AI_MODEL # Default, override in subclass
        self.provider_type: str = config.get("provider_type", "unknown") # Default to config value
        self._is_connected = False
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to the external service.
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close connection and cleanup resources.
        """
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """
        Check if the provider is healthy and operational.

        Returns:
            True if healthy, False otherwise.
        """
        pass

    @abstractmethod
    async def execute(self, request: IntegrationRequest) -> IntegrationResponse:
        """
        Execute a request against the provider.

        Args:
            request: The standardized request object

        Returns:
            The standardized response object
        """
        pass

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._is_connected

    def get_status(self) -> ProviderStatus:
        """Get the current status of the provider."""
        if self._is_connected:
            return ProviderStatus.ACTIVE
        return ProviderStatus.INACTIVE
