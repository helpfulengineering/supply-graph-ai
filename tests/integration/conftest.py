"""Shared fixtures for integration tests.

These tests run the full ASGI stack in-process via FastAPI's TestClient, so
no live server is required.  Set STORAGE_PROVIDER=local (or leave unset —
conftest sets it) and opt in with RUN_LIVE_API_TESTS=1.
"""

from __future__ import annotations

import os
import tempfile

import pytest

# Force local storage for the in-process app.
#
# `setdefault` is NOT enough here: importing any app module runs
# `src.config.schema`'s import-time `load_dotenv()`, which populates `os.environ`
# from the project `.env` (e.g. `STORAGE_PROVIDER=azure_blob` pointed at a live
# container). In a full-suite run that happens *before* this conftest is imported
# (an earlier test package pulls in the app), so a plain `setdefault` is a silent
# no-op and the integration tests end up hitting live storage — slow enough to
# trip the pytest timeout and hang `make ready`. Hard-assign so these in-process
# tests are always hermetic regardless of collection/import order.
_STORAGE_DIR = tempfile.mkdtemp(prefix="ohm-integ-")
os.environ["STORAGE_PROVIDER"] = "local"
os.environ["LOCAL_STORAGE_PATH"] = _STORAGE_DIR
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

    # Defensively re-assert local storage in case an earlier test mutated the
    # environment, then drop any singleton services initialised by earlier tests
    # so they rebuild against the local-storage config (get_settings() is
    # uncached and reads os.environ live).
    os.environ["STORAGE_PROVIDER"] = "local"
    os.environ["LOCAL_STORAGE_PATH"] = _STORAGE_DIR
    BaseService._instances.clear()

    from src.core.main import app

    with TestClient(
        app, base_url="http://testserver/v1", raise_server_exceptions=False
    ) as c:
        yield c

    import shutil

    shutil.rmtree(_STORAGE_DIR, ignore_errors=True)
    BaseService._instances.clear()
