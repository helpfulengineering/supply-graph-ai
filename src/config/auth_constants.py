"""Canonical auth mode constants shared by config and services."""

AUTH_MODE_ENV = "env"
AUTH_MODE_STORAGE = "storage"
AUTH_MODE_HYBRID = "hybrid"

AUTH_MODES = {
    "env": AUTH_MODE_ENV,
    "storage": AUTH_MODE_STORAGE,
    "hybrid": AUTH_MODE_HYBRID,
}
