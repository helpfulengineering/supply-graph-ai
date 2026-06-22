"""Shared fixtures for integration tests.

These tests run the full ASGI stack in-process via FastAPI's TestClient, so
no live server is required.  Set STORAGE_PROVIDER=local (or leave unset —
conftest sets it) and opt in with RUN_LIVE_API_TESTS=1.
"""

from __future__ import annotations

import os
import tempfile

import pytest

# Set storage env vars before any app module is imported.
# setdefault lets callers override from the shell (e.g. a real dev server run).
_STORAGE_DIR = tempfile.mkdtemp(prefix="ohm-integ-")
os.environ.setdefault("STORAGE_PROVIDER", "local")
os.environ.setdefault("LOCAL_STORAGE_PATH", _STORAGE_DIR)
# Ensure federation doesn't try to create Docker-only paths.
os.environ.setdefault("OHM_FEDERATION_ENABLED", "false")


@pytest.fixture(scope="session")
def client():
    """Session-scoped TestClient that runs the full OHM ASGI app in-process.

    All integration tests share one app instance and one storage directory so
    that fixtures which create-then-delete resources don't interfere with
    each other across modules.
    """
    from src.core.services.base import BaseService
    from fastapi.testclient import TestClient
    from src.core.main import app

    # Clear any singleton services initialised by earlier unit tests so they
    # pick up the local-storage config set above.
    BaseService._instances.clear()

    with TestClient(
        app, base_url="http://testserver/v1", raise_server_exceptions=False
    ) as c:
        yield c

    import shutil

    shutil.rmtree(_STORAGE_DIR, ignore_errors=True)
    BaseService._instances.clear()
