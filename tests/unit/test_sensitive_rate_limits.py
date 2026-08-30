"""Recovery redemption gets its own small budget (#414).

It takes a bearer secret and hands back a working credential, so a burst of
requests against it is an attack rather than a busy user. This does not defend
against *guessing* — a recovery code is 256 bits of CSPRNG output, and saying a
rate limit is what stands between an attacker and a correct guess would be
theatre. What it bounds is the cost of hammering the endpoint, and it makes a
sustained attempt visible instead of lost inside an allowance shared with page
loads.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.api.middleware import SENSITIVE_PATH_LIMITS, RateLimitingMiddleware


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.add_middleware(RateLimitingMiddleware, requests_per_minute=100)

    @app.post("/v1/api/identity/recover")
    async def recover():
        return {"ok": True}

    @app.get("/v1/api/okh")
    async def browse():
        return {"ok": True}

    return TestClient(app)


def test_recovery_runs_out_long_before_the_generic_budget(client):
    limit = SENSITIVE_PATH_LIMITS["/v1/api/identity/recover"]
    codes = [
        client.post("/v1/api/identity/recover").status_code for _ in range(limit + 3)
    ]

    assert codes[:limit] == [200] * limit
    assert codes[limit] == 429, f"still allowed after {limit} attempts: {codes}"
    assert 429 in codes


def test_exhausting_recovery_does_not_lock_a_user_out_of_the_site(client):
    """Separate namespaces: otherwise anyone could deny an address the whole
    API by burning its recovery allowance."""
    for _ in range(SENSITIVE_PATH_LIMITS["/v1/api/identity/recover"] + 2):
        client.post("/v1/api/identity/recover")

    assert client.get("/v1/api/okh").status_code == 200


def test_ordinary_browsing_cannot_exhaust_the_recovery_budget(client):
    """And the other direction — a busy page must not spend the small budget."""
    for _ in range(30):
        assert client.get("/v1/api/okh").status_code == 200

    assert client.post("/v1/api/identity/recover").status_code == 200


def test_the_limit_is_far_below_the_generic_one():
    """A guard that is not actually tighter is decoration."""
    assert SENSITIVE_PATH_LIMITS["/v1/api/identity/recover"] < 20
