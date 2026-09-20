"""What the served OpenAPI document tells a client about talking to `/v1`.

Two things a clean-box tester tripped on, and only one was the server's fault.

**Not a bug: relative paths.** `/v1/openapi.json` lists `/api/identity/whoami`,
and `/api/identity/whoami` 404s on the API port. It looked like drift. It is what
OpenAPI 3.1 asks for: the document declares `servers: [{"url": "/v1"}]`, and a
path is "appended (no relative URL resolution) to the expanded URL from the
Server Object's url field"; a server url "MAY be relative, to indicate that the
host location is relative to the location where the OpenAPI document is being
served". Swagger UI and generators resolve it. The frontend depends on it too:
`schema.d.ts` is rooted at `/api/...` and its client sets `/v1` as the base. So
the first two tests **freeze** the current form. Moving `/v1` into the path keys
would look like a fix and would regenerate the client types for nothing.

**A bug: the declared auth scheme.** The document declared `apiKey` in the
`Authorization` header, while the server rejects exactly that with "Expected
'Bearer <token>'". A generated client, or a person in Swagger UI, sent what the
document said and was refused. The scheme must say `http` / `bearer`.

The last two tests pin the *runtime* messages, which the change must not touch:
only what the document declares was wrong.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from fastapi.testclient import TestClient  # noqa: E402

from src.core.main import app  # noqa: E402

pytestmark = pytest.mark.contract


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def spec(client: TestClient) -> dict:
    response = client.get("/v1/openapi.json")
    assert response.status_code == 200
    return response.json()


def test_the_server_url_is_relative_and_the_paths_are_relative_to_it(spec) -> None:
    assert spec["servers"] == [{"url": "/v1"}], (
        "The paths below are relative to this; changing it changes what every "
        "generated client requests."
    )
    prefixed = [p for p in spec["paths"] if p.startswith("/v1/") or p == "/v1"]
    assert not prefixed, (
        "Paths carry the server prefix already, so a client would request "
        f"/v1/v1/...: {prefixed[:3]}"
    )


def test_the_declared_security_scheme_is_http_bearer(spec) -> None:
    schemes = spec["components"]["securitySchemes"]
    assert schemes, "the document declares no security scheme at all"
    wrong = {
        name: scheme
        for name, scheme in schemes.items()
        if not (scheme["type"] == "http" and scheme["scheme"].lower() == "bearer")
    }
    assert not wrong, (
        "The server requires 'Authorization: Bearer <token>'. A scheme declared "
        f"any other way sends clients the wrong header: {wrong}"
    )


def test_a_missing_token_is_refused_with_the_expected_form(client: TestClient) -> None:
    """Runtime control: unchanged by how the scheme is declared."""
    response = client.get("/v1/api/identity/whoami")

    assert response.status_code == 401
    assert "Bearer <token>" in response.json()["detail"]


def test_a_non_bearer_scheme_is_refused_with_the_same_message(
    client: TestClient,
) -> None:
    """Runtime control: the server's own message for exactly what apiKey declared."""
    response = client.get(
        "/v1/api/identity/whoami", headers={"Authorization": "Basic dXNlcjpwYXNz"}
    )

    assert response.status_code == 401
    assert (
        response.json()["detail"]
        == "Invalid authentication token format. Expected 'Bearer <token>'"
    )
