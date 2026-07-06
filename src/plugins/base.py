from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional
from fastapi import FastAPI
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

from src.core.models.okh import OKHManifest
from src.core.models.okw import ManufacturingFacility


class PluginCapability(Enum):
    """Capabilities that a plugin can declare for least-privilege access."""
    NETWORK_EGRESS = "network:egress"
    STORAGE_READ = "storage:read"
    STORAGE_WRITE = "storage:write"


class PluginSettings(BaseSettings):
    """Base class for plugin-specific settings."""
    model_config = ConfigDict(env_file=".env", extra="ignore")


class BasePlugin(ABC):
    """Abstract base class for all integration plugins."""

    def __init__(self, settings: Optional[PluginSettings] = None):
        self.settings = settings

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the plugin."""
        pass

    @property
    def plugin_api_version(self) -> str:
        """The version of the plugin API this plugin was built against."""
        return "0.1.0"

    @property
    def capabilities(self) -> List[PluginCapability]:
        """List of capabilities required by the plugin."""
        return []

    @abstractmethod
    def initialize(self) -> None:
        """Synchronous initialization of the plugin."""
        pass

    @abstractmethod
    def register_routes(self, app: FastAPI) -> None:
        """Register plugin-specific routes with the FastAPI application."""
        pass

    async def on_startup(self) -> None:
        """Async hook called during application startup."""
        pass

    async def on_shutdown(self) -> None:
        """Async hook called during application shutdown."""
        pass

    def register_event_handlers(self) -> None:
        """Stub for future internal event bus integration."""
        pass


class DataSourcePlugin(BasePlugin, ABC):
    """Specialized plugin class for data-source / interop adapters."""

    @abstractmethod
    def fetch_records(self) -> Iterable[Dict[str, Any]]:
        """Fetch raw records from the external data source."""
        pass

    @abstractmethod
    def normalize_to_okh(self, record: Dict[str, Any]) -> Optional[OKHManifest]:
        """Normalize a raw record to an OKHManifest."""
        pass

    @abstractmethod
    def normalize_to_okw(self, record: Dict[str, Any]) -> Optional[ManufacturingFacility]:
        """Normalize a raw record to a ManufacturingFacility."""
        pass
