import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from src.plugins.manager import PluginManager
from src.plugins.base import BasePlugin, PluginSettings

class MockPlugin(BasePlugin):
    @property
    def name(self):
        return "mock_plugin"

    def initialize(self):
        self.initialized = True

    def register_routes(self, app):
        self.routes_registered = True

    async def on_startup(self):
        self.started = True

@pytest.fixture
def plugin_manager():
    from src.config import settings
    settings.ACTIVE_PLUGINS = []
    PluginManager.reset_instance()
    pm = PluginManager.get_instance()
    pm.reload_config()
    return pm

def test_plugin_manager_singleton():
    pm1 = PluginManager.get_instance()
    pm2 = PluginManager.get_instance()
    assert pm1 is pm2

def test_plugin_manager_gated_loading(plugin_manager):
    from src.config import settings
    settings.ACTIVE_PLUGINS = ["non_existent_plugin"]
    plugin_manager.reload_config()

    with patch("src.plugins.manager.importlib.import_module") as mock_import:
        mock_import.side_effect = ImportError("Module not found")
        plugin_manager.discover_and_load()
        assert len(plugin_manager._plugins) == 0

@pytest.mark.anyio
async def test_plugin_lifecycle_hooks(plugin_manager):
    mock_plugin = MockPlugin()
    mock_plugin.initialize = MagicMock()
    # Create an async mock for on_startup
    mock_plugin.on_startup = MagicMock(return_value=MagicMock(__await__=lambda x: iter([]).__next__()))
    # Actually, AsyncMock is better if available
    from unittest.mock import AsyncMock
    mock_plugin.on_startup = AsyncMock()

    mock_plugin.register_routes = MagicMock()

    plugin_manager._plugins["mock"] = mock_plugin

    # Test route registration
    app = FastAPI()
    plugin_manager.register_all_routes(app)
    mock_plugin.register_routes.assert_called_once_with(app)

    # Test startup hook
    await plugin_manager.startup()
    mock_plugin.on_startup.assert_called_once()

def test_plugin_settings_initialization():
    class CustomSettings(PluginSettings):
        FOO: str = "bar"

    settings = CustomSettings()
    assert settings.FOO == "bar"
