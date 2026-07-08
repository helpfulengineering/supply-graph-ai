"""HTTP exception handler attaches X-Request-Id."""

from __future__ import annotations

import pytest
from fastapi import HTTPException, Request
from starlette.datastructures import Headers

from src.core.api.constants.headers import HEADER_REQUEST_ID
from src.core.api.error_handlers import http_exception_handler

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_http_exception_handler_sets_request_id_header():
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/api/match",
        "headers": [],
    }
    request = Request(scope)
    request.state.request_id = "req-test-123"
    exc = HTTPException(status_code=503, detail="Matching service unavailable")

    response = await http_exception_handler(request, exc)

    assert response.status_code == 503
    assert response.headers[HEADER_REQUEST_ID] == "req-test-123"
    body = response.body.decode()
    assert "req-test-123" in body
