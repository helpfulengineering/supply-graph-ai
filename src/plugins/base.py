from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from fastapi import FastAPI
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


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
