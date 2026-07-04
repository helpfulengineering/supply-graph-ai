import os
import importlib
import logging
from typing import Dict, List, Type
from fastapi import FastAPI

from src.config import settings
from src.core.utils.logging import get_logger
from src.plugins.base import BasePlugin

logger = get_logger(__name__)

class PluginManager:
    _instance = None
    _plugins: Dict[str, BasePlugin] = {}

    def __init__(self):
        self.active_plugin_names = settings.ACTIVE_PLUGINS
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))

    def reload_config(self):
        """Reload active plugin names from settings (useful for testing)."""
        from src.config import settings
        self.active_plugin_names = settings.ACTIVE_PLUGINS

    @classmethod
    def get_instance(cls) -> "PluginManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None
        cls._plugins = {}

    def discover_and_load(self):
        """Discover and load active plugins based on settings."""
        if not self.active_plugin_names:
            logger.info("No active plugins configured.")
            return

        for plugin_name in self.active_plugin_names:
            try:
                self._load_plugin(plugin_name)
            except Exception as e:
                logger.error(f"Failed to load plugin '{plugin_name}': {e}", exc_info=True)

    def _load_plugin(self, plugin_name: str):
        """Dynamically import and instantiate a plugin."""
        module_path = f"src.plugins.{plugin_name}.plugin"
        try:
            module = importlib.import_module(module_path)
            plugin_class: Type[BasePlugin] = getattr(module, "Plugin")

            # Check if there's a custom settings class
            plugin_settings = None
            try:
                settings_module = importlib.import_module(f"src.plugins.{plugin_name}.config")
                settings_class = getattr(settings_module, "PluginSettings")
                plugin_settings = settings_class()
            except (ImportError, AttributeError):
                logger.debug(f"No custom settings found for plugin '{plugin_name}'")

            instance = plugin_class(settings=plugin_settings)
            instance.initialize()
            self._plugins[plugin_name] = instance
            logger.info(f"Successfully loaded and initialized plugin: {plugin_name}")
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Could not find 'Plugin' class in {module_path}") from e

    def register_all_routes(self, app: FastAPI):
        """Register routes for all loaded plugins."""
        for name, plugin in self._plugins.items():
            logger.info(f"Registering routes for plugin: {name}")
            plugin.register_routes(app)

    async def startup(self):
        """Trigger on_startup hook for all plugins."""
        for name, plugin in self._plugins.items():
            logger.info(f"Starting up plugin: {name}")
            await plugin.on_startup()

    async def shutdown(self):
        """Trigger on_shutdown hook for all plugins."""
        for name, plugin in self._plugins.items():
            logger.info(f"Shutting down plugin: {name}")
            await plugin.on_shutdown()

    def get_plugin(self, name: str) -> BasePlugin:
        return self._plugins.get(name)
