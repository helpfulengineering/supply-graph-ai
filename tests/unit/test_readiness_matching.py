"""Readiness probe includes matching service when eager init is enabled."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


@pytest.fixture
def client():
    with patch("src.core.main.settings.MATCHING_EAGER_INIT", False):
        from src.core.main import app

        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client


def test_readiness_reports_matching_service_check(client):
    with (
        patch(
            "src.core.main.MatchingService.is_ready",
            return_value=False,
        ),
        patch("src.core.main.settings.MATCHING_EAGER_INIT", True),
    ):
        response = client.get("/health/readiness")
    assert response.status_code == 503
    payload = json.loads(response.text)
    assert payload["checks"]["matching_service"] is False
    assert any("Matching service" in err for err in payload.get("errors", []))


def test_readiness_ok_when_matching_ready(client):
    with (
        patch(
            "src.core.main.MatchingService.is_ready",
            return_value=True,
        ),
        patch("src.core.main.settings.MATCHING_EAGER_INIT", True),
        patch(
            "src.core.main.StorageService.get_instance",
            return_value=object(),
        ),
        patch(
            "src.core.main.AuthenticationService.get_instance",
            return_value=object(),
        ),
        patch(
            "src.core.main.DomainRegistry.get_registered_domains",
            return_value=["manufacturing", "cooking"],
        ),
    ):
        response = client.get("/health/readiness")
    assert response.status_code == 200
    payload = json.loads(response.text)
    assert payload["status"] == "ready"
    assert payload["checks"]["matching_service"] is True
