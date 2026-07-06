# Integration Plugin System

OHM supports a modular plugin system for external integrations. This allows for keeping the core platform agnostic while enabling specialized commercial lifecycles or connecting to external data sources.

## Classes of Plugins

Plugins in OHM generally fall into two categories:

1.  **Data-source / interop adapters**: These plugins bring external data into OHM's model (e.g., fetching design or facility data from platforms like Appropedia or fablabs.io and normalizing it to OKH/OKW).
2.  **Business-logic / connector plugins**: These plugins sit on top of OHM, consuming its data or bridging to external tools for specific workflows (e.g., cost estimation, RFQ, or manufacturing coordination).

## Architecture

Plugins live in `src/plugins/` and are managed by the `PluginManager`. Each plugin is a self-contained directory.

### Directory Structure

```text
src/plugins/my_integration/
├── __init__.py
├── plugin.py    # Main entry point (exports class Plugin)
├── routes.py    # FastAPI routes
├── service.py   # Business logic (optional)
├── config.py    # Private configuration (Pydantic BaseSettings)
└── tests/       # Plugin-specific tests
```

## Plugin Contract

All plugins must inherit from `BasePlugin` in `src/plugins/base.py`.

### Capabilities

Plugins declare the capabilities they require for least-privilege access:
- `NETWORK_EGRESS`: Permission to make external network requests.
- `STORAGE_READ`: Permission to read from OHM's core storage.
- `STORAGE_WRITE`: Permission to write to OHM's core storage.

### Versioning

Each plugin must declare the `plugin_api_version` it was built against (e.g., `"0.1.0"`).

### Data-Source Plugins

For plugins that import data, inherit from `DataSourcePlugin`. This class requires implementing:
- `fetch_records()`: An iterable that yields raw records from the source.
- `normalize_to_okh(record)`: Normalizes a raw record into an `OKHManifest`.
- `normalize_to_okw(record)`: Normalizes a raw record into a `ManufacturingFacility`.

**Note**: All imported data is treated as unverified by default (`is_verified=False`) and should carry its `provenance` (the source of the data).

## Creating a Plugin

The easiest way to start is by copying the `src/plugins/template/` directory.

### Registration

To activate a plugin, add its directory name to the `OHM_ACTIVE_PLUGINS` environment variable (comma-separated).

```bash
export OHM_ACTIVE_PLUGINS=my_integration
```

Use `OHM_STRICT_PLUGINS=true` to force the application to hard-fail if a plugin fails to load during startup.

## Lifecycle Hooks

- `initialize()`: Synchronous setup called after import.
- `register_routes(app)`: Mounts FastAPI routes.
- `on_startup()`: Async hook called during application startup.
- `on_shutdown()`: Async hook called during application shutdown.
