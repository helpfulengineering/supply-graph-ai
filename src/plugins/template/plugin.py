from fastapi import FastAPI
from src.plugins.base import BasePlugin, PluginCapability
from .routes import router

class Plugin(BasePlugin):
    @property
    def name(self) -> str:
        return "template"

    @property
    def plugin_api_version(self) -> str:
        return "0.1.0"

    @property
    def capabilities(self) -> list[PluginCapability]:
        return [PluginCapability.NETWORK_EGRESS]

    def initialize(self) -> None:
        # One-time synchronous setup
        pass

    def register_routes(self, app: FastAPI) -> None:
        # Mount your APIRouter
        app.include_router(router, prefix="/api/v1/template", tags=["template"])

    async def on_startup(self) -> None:
        # Async setup (e.g. initializing HTTP clients)
        pass

    async def on_shutdown(self) -> None:
        # Graceful teardown
        pass
