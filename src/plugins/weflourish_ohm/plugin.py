from fastapi import FastAPI
from src.plugins.base import BasePlugin
from .routes import router
from .service import WeFlourishRFQService
from .config import PluginSettings

class Plugin(BasePlugin):
    @property
    def name(self) -> str:
        return "weflourish_ohm"

    def initialize(self) -> None:
        """Initialize the WeFlourish RFQ service with plugin settings."""
        WeFlourishRFQService.get_instance(settings=self.settings)

    def register_routes(self, app: FastAPI) -> None:
        """Mount the plugin routes."""
        app.include_router(router)

    async def on_startup(self) -> None:
        """Lifecycle hook: handle any async startup tasks."""
        pass

    async def on_shutdown(self) -> None:
        """Lifecycle hook: handle any async cleanup tasks."""
        pass
