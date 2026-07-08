"""Unit tests for MatchingService startup readiness (issue #270)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.core.services.matching_service import MatchingService

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset_matching_singleton():
    MatchingService._instance = None
    yield
    MatchingService._instance = None


def test_is_ready_false_before_init():
    assert MatchingService.is_ready() is False


@pytest.mark.asyncio
async def test_is_ready_true_after_initialize():
    service = MatchingService()
    service._initialized = True
    MatchingService._instance = service
    assert MatchingService.is_ready() is True


@pytest.mark.asyncio
async def test_get_instance_clears_singleton_on_init_failure():
    with patch.object(
        MatchingService,
        "initialize",
        new_callable=AsyncMock,
        side_effect=RuntimeError("init failed"),
    ):
        with pytest.raises(RuntimeError, match="init failed"):
            await MatchingService.get_instance()
    assert MatchingService._instance is None


@pytest.mark.asyncio
async def test_get_matching_service_timeout_raises_503():
    from fastapi import HTTPException

    from src.core.api.routes.match import get_matching_service

    with patch(
        "src.core.api.routes.match.asyncio.wait_for",
        new_callable=AsyncMock,
        side_effect=TimeoutError(),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_matching_service()
    assert exc_info.value.status_code == 503
    assert "timed out" in str(exc_info.value.detail).lower()
