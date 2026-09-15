"""A wildcard CORS origin must never come with credentials (#462).

`allow_credentials=True` alongside `allow_origins=["*"]` does not mean what it
looks like. Starlette will not send `Access-Control-Allow-Origin: *` with
credentials, because browsers reject that pairing — so it **echoes the caller's
own `Origin` back instead**, individually approving every origin on earth for
credentialed cross-origin requests. The wildcard a browser refuses becomes an
echo a browser accepts.

Nothing rides on it today: authentication is a bearer token the frontend
attaches explicitly, and browsers do not send those automatically cross-origin.
It fires the moment any cookie exists. So these tests assert the *header on the
wire*, not the setting — the setting was never the thing that was wrong.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.config.schema import cors_allow_credentials  # noqa: E402

pytestmark = pytest.mark.unit

_HOSTILE = "https://attacker.example"


def _preflight(origins: list[str]):
    """Build an app with these origins and send it a credentialed preflight."""
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=cors_allow_credentials(origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/probe")
    async def probe():
        return {"ok": True}

    return TestClient(app).options(
        "/probe",
        headers={
            "Origin": _HOSTILE,
            "Access-Control-Request-Method": "GET",
        },
    )


def test_wildcard_never_offers_credentials() -> None:
    """The defect, asserted on the wire."""
    resp = _preflight(["*"])
    assert resp.headers.get("access-control-allow-credentials") is None, (
        "A wildcard node offered credentials; a hostile origin would be "
        "individually approved for credentialed requests."
    )


def test_wildcard_does_not_echo_a_hostile_origin() -> None:
    """The mechanism: without credentials, Starlette answers `*`, not the echo."""
    resp = _preflight(["*"])
    assert resp.headers.get("access-control-allow-origin") == "*", (
        "Expected the literal wildcard. An echoed Origin is what "
        "allow_credentials=True produced, and is the defect itself."
    )


def test_calibration_an_allowlist_still_offers_credentials() -> None:
    """Control: the assertion above can distinguish, rather than always holding.

    Without this, both tests would pass against a CORS layer that had simply
    been turned off, and neither would be evidence of anything.
    """
    resp = _preflight([_HOSTILE])
    assert resp.headers.get("access-control-allow-credentials") == "true"
    assert resp.headers.get("access-control-allow-origin") == _HOSTILE


@pytest.mark.parametrize(
    "origins,expected",
    [
        (["*"], False),
        ([], False),
        (["https://a.example"], True),
        (["https://a.example", "*"], False),
    ],
)
def test_credentials_are_derived_from_the_origins(origins, expected) -> None:
    """Including the mixed case: one wildcard poisons an otherwise real list."""
    assert cors_allow_credentials(origins) is expected


def test_the_real_app_is_wired_to_the_derived_value() -> None:
    """The tests above would pass on a correct helper and an unwired app.

    `main.py` is where the defect actually lived, so assert the middleware the
    application really mounts, not a stand-in built here.
    """
    from starlette.middleware.cors import CORSMiddleware

    from src.config import settings
    from src.core.main import app

    cors = [m for m in app.user_middleware if m.cls is CORSMiddleware]
    assert len(cors) == 1, "Expected exactly one CORS middleware on the app"
    configured = cors[0].kwargs["allow_credentials"]
    assert configured is settings.CORS_ALLOW_CREDENTIALS, (
        "The app hardcodes allow_credentials instead of deriving it from the "
        "configured origins."
    )
    if "*" in settings.CORS_ORIGINS:
        assert configured is False
