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


@pytest.fixture
def matchable_design(client):
    """Create a design that matching will actually consider, and clean it up.

    Records are created ``private`` and an anonymous list returns only
    shareable ones, so a design created in-process is invisible to an anonymous
    match — which is how three separate tests came to assert against a list
    that was always empty. Making the intent explicit here beats leaving each
    test to rediscover it.

    Cleans up because the integration client and its storage are session-scoped:
    records left behind change what every later test sees.
    """
    created: list[str] = []

    def make(content: dict) -> str:
        resp = client.post("/api/okh/create", json={"content": content})
        assert resp.status_code == 201, resp.text
        record_id = resp.json()["okh"]["id"]
        created.append(record_id)
        shared = client.put(
            f"/api/okh/{record_id}/visibility", json={"visibility": "public"}
        )
        assert shared.status_code == 200, shared.text
        return record_id

    yield make

    for record_id in created:
        client.delete(f"/api/okh/{record_id}")
