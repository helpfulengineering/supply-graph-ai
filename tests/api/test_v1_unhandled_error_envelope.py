"""An unhandled exception under `/v1` answers with the JSON error envelope.

`/v1` is a mounted sub-application (`app.mount("/v1", api_v1)`), and Starlette
gives every application its own outermost error middleware. Exception handlers
registered on the parent `app` are therefore invisible to it: the sub-app's
middleware finds no handler, answers `text/plain "Internal Server Error"`, and
re-raises — and the parent's handler then runs and logs, but the response has
already started, so what it built is thrown away.

An operator saw exactly that: the container log named the cause
(`PermissionError: /home/ohm`) and the HTTP client got two words with no request
id to find the log line by. It affects every unhandled exception under `/v1`,
which is why this asserts the wiring rather than any one route.

Deliberately **not** changed: `HTTPException` and validation errors under `/v1`
still answer FastAPI's `{"detail": ...}`. The CLI reads that key in four places,
and an external client may too; the envelope has no `detail`. The last two tests
pin that, so widening the change later is a decision and not an accident.
"""

from __future__ import annotations

import logging
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.core.main import api_v1, app  # noqa: E402

pytestmark = pytest.mark.contract

_BOOM = "/_test_unhandled_boom"
_TEAPOT = "/_test_http_exception"


@pytest.fixture
def client():
    """The real app, with two throwaway routes on the real `/v1` sub-app.

    Routes are removed afterwards: the parity suite compares the live OpenAPI
    document against the committed client types, so a test route left behind
    would fail an unrelated test.
    """

    def boom():
        raise PermissionError(13, "Permission denied", "/home/ohm")

    def teapot():
        raise HTTPException(status_code=418, detail="short and stout")

    api_v1.add_api_route(_BOOM, boom, methods=["GET"], include_in_schema=False)
    api_v1.add_api_route(_TEAPOT, teapot, methods=["GET"], include_in_schema=False)
    added = api_v1.router.routes[-2:]
    try:
        # The server-side exception is re-raised after the response is sent, as
        # it is under a real server; the client must not see it.
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        for route in added:
            api_v1.router.routes.remove(route)


def test_unhandled_exception_returns_the_json_envelope(client) -> None:
    response = client.get(f"/v1{_BOOM}")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json"), (
        "An unhandled /v1 error answered "
        f"{response.headers['content-type']!r}: {response.text!r}. The exception "
        "handlers are registered on the parent app, which the mounted /v1 "
        "sub-app cannot see."
    )
    body = response.json()
    assert body["request_id"], "the client has no id to find the log line by"
    assert body["errors"], "the envelope carries a structured error list"
    assert response.headers["x-request-id"] == body["request_id"]


def test_an_unhandled_exception_is_logged_once(
    client, caplog: pytest.LogCaptureFixture
) -> None:
    """Two apps each have a handler now; the error must still log a single time.

    Starlette re-raises after a handler answers, so the parent's handler runs as
    well, too late to send anything. Without a guard every 500 logs a full
    traceback twice and doubles whatever counts them.
    """
    with caplog.at_level(logging.ERROR):
        client.get(f"/v1{_BOOM}")

    logged = [r for r in caplog.records if "Unhandled exception" in r.getMessage()]
    assert len(logged) == 1, f"logged {len(logged)} times"


def test_an_http_exception_still_answers_detail(client) -> None:
    """Pinned on purpose: the CLI reads `detail`; the envelope has none."""
    response = client.get(f"/v1{_TEAPOT}")

    assert response.status_code == 418
    assert response.json() == {"detail": "short and stout"}


def test_an_unknown_route_still_answers_detail(client) -> None:
    response = client.get("/v1/api/definitely-not-a-route")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
