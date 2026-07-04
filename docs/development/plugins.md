# Integration Plugin System

OHM supports a modular plugin system for external integrations (like WeFlourish, ERPs, or custom supply chain platforms). This allows for keeping the core platform agnostic while enabling specialized commercial lifecycles.

## Architecture

Plugins live in `src/plugins/` and are managed by the `PluginManager`. Each plugin is a self-contained directory with its own routes, services, and configuration.

### Directory Structure

```text
src/plugins/my_integration/
├── __init__.py
├── plugin.py    # Main entry point (exports class Plugin)
├── routes.py    # FastAPI routes
├── service.py   # Business logic
└── config.py    # Private configuration (Pydantic BaseSettings)
```

## Creating a Plugin

### 1. Define Configuration (`config.py`)

Extend `PluginSettings` to define your environment variables.

```python
from src.plugins.base import PluginSettings as BasePluginSettings

class PluginSettings(BasePluginSettings):
    MY_API_KEY: str
    MY_API_URL: str = "https://api.example.com"

    class Config:
        env_prefix = "MY_INTEG_"
```

### 2. Implement the Plugin Class (`plugin.py`)

Your plugin must export a class named `Plugin` that inherits from `BasePlugin`.

```python
from fastapi import FastAPI
from src.plugins.base import BasePlugin
from .routes import router

class Plugin(BasePlugin):
    @property
    def name(self) -> str:
        return "my_integration"

    def initialize(self) -> None:
        # One-time synchronous setup
        pass

    def register_routes(self, app: FastAPI) -> None:
        # Mount your APIRouter
        app.include_router(router)

    async def on_startup(self) -> None:
        # Async setup (e.g. initializing HTTP clients)
        pass

    async def on_shutdown(self) -> None:
        # Graceful teardown
        pass
```

### 3. Register the Plugin

To activate a plugin, add its directory name to the `OHM_ACTIVE_PLUGINS` environment variable (comma-separated).

```bash
export OHM_ACTIVE_PLUGINS=weflourish_ohm,my_integration
```

## Lifecycle Hooks

- `initialize()`: Called immediately after the plugin is imported.
- `register_routes(app)`: Called during FastAPI setup to mount routes.
- `on_startup()`: Called during the FastAPI `lifespan` startup phase.
- `on_shutdown()`: Called during the FastAPI `lifespan` shutdown phase.

## Best Practices

1. **Keep Core Agnostic**: Avoid importing plugin logic into `src/core`. If the core needs to interact with plugins, use an event bus or standard interfaces.
2. **Use Core Models**: Use universal primitives from `src/core/models` (like `Bid` and `Quote`) whenever possible.
3. **Private Configuration**: Use the `PluginSettings` class to keep integration-specific environment variables isolated.
