"""Transport headers are decisions now, not defaults (#412).

Neither of these was a live credential leak, and overstating them would be its
own kind of wrong. They were blanket values applied to an API that had just
started serving per-user private data, and both deserved an actual choice.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.api.middleware import (
    DEFAULT_CORS_ALLOW_ORIGIN,
    HSTS_MAX_AGE_SECONDS,
    SecurityHeadersMiddleware,
    cors_allow_origin,
)


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/thing")
    async def thing():
        return {"ok": True}

    return TestClient(app)


def test_hsts_is_sent_over_https(client):
    resp = client.get("https://testserver/thing")
    header = resp.headers["strict-transport-security"]

    assert f"max-age={HSTS_MAX_AGE_SECONDS}" in header
    assert "includeSubDomains" in header


def test_hsts_is_not_sent_over_plain_http(client):
    """Pinning localhost to https for a year is a genuinely painful thing to
    undo on a developer's own machine."""
    resp = client.get("http://testserver/thing")

    assert "strict-transport-security" not in resp.headers


def test_no_preload_directive():
    """Preload lists are effectively irreversible and removal takes months, so
    it is an operator's decision about their own domain — not a default."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/x")
    async def x():
        return {}

    resp = TestClient(app).get("https://testserver/x")
    assert "preload" not in resp.headers["strict-transport-security"]


def test_cors_default_is_unchanged_so_no_deployment_breaks(client, monkeypatch):
    monkeypatch.delenv("OHM_CORS_ALLOW_ORIGIN", raising=False)

    assert cors_allow_origin() == DEFAULT_CORS_ALLOW_ORIGIN == "*"
    assert (
        client.get("http://testserver/thing").headers["access-control-allow-origin"]
        == "*"
    )


def test_cors_origin_is_configurable(monkeypatch):
    """A node that is not a public catalogue can narrow it."""
    monkeypatch.setenv("OHM_CORS_ALLOW_ORIGIN", "https://ohm.example.org")

    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/x")
    async def x():
        return {}

    resp = TestClient(app).get("http://testserver/x")
    assert resp.headers["access-control-allow-origin"] == "https://ohm.example.org"


def test_credentials_are_never_allowed(client):
    """What keeps the wildcard from being a credential leak: without this
    header a third-party page cannot make a request carrying a viewer's token,
    whatever origin is allowed to read the response."""
    resp = client.get("http://testserver/thing")

    assert "access-control-allow-credentials" not in resp.headers
