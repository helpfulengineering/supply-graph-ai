"""Tests for unauthenticated-first GitHub supplementary metadata fetch.

Verifies that:
  - Public repos are always tried without a token first.
  - A token in the environment is NOT used unless the public request fails.
  - A 401 on the unauthenticated request triggers a token-based retry.
  - A 401 on the token-based retry logs a warning but does not raise.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.generation.platforms.local_git import LocalGitExtractor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_extractor() -> LocalGitExtractor:
    """Return a minimal LocalGitExtractor without touching the filesystem."""
    extractor = object.__new__(LocalGitExtractor)
    return extractor


def _mock_response(status_code: int, json_body: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json = MagicMock(return_value=json_body or {})
    return resp


# ---------------------------------------------------------------------------
# Tests: unauthenticated first
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_public_repo_fetched_without_token(monkeypatch):
    """A public repo must be fetched without an Authorization header even when a
    token is present in the environment."""
    extractor = _make_extractor()

    # Simulate a token in env — it should NOT be used for the initial request
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token-abc")

    captured_headers: list[dict] = []

    async def _fake_fetch(auth_token):
        captured_headers.append({"has_auth": auth_token is not None})
        return {}

    with patch.object(
        extractor.__class__,
        "_load_github_token_from_env",
        return_value="fake-token-abc",
    ):
        # Patch _fetch_github_supplementary_metadata internals via a controlled
        # re-implementation that records call order.
        with patch(
            "src.core.generation.platforms.local_git.LocalGitExtractor"
            "._load_github_token_from_env",
            return_value="fake-token-abc",
        ):
            pass  # token is "available"

    # Directly test the function call order by inspecting actual HTTP calls
    # through httpx mock.
    import httpx

    responses_queue = [
        _mock_response(200, {"topics": ["microscopy"], "default_branch": "master"}),
        _mock_response(200, {"tag_name": "v7.0.0"}),
    ]

    async def mock_get(url, **kwargs):
        return responses_queue.pop(0)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=mock_get)

    headers_seen: list[dict] = []

    original_async_client = httpx.AsyncClient

    class _RecordingClient:
        def __init__(self, headers=None, timeout=None):
            headers_seen.append(dict(headers or {}))
            self._inner = mock_client

        async def __aenter__(self):
            return mock_client

        async def __aexit__(self, *args):
            return False

    with patch("httpx.AsyncClient", _RecordingClient):
        with patch.object(
            extractor, "_load_github_token_from_env", return_value="fake-token-abc"
        ):
            result = await extractor._fetch_github_supplementary_metadata(
                "rwb27", "openflexure_microscope"
            )

    # First (and only) request should carry NO Authorization header
    assert headers_seen, "Expected at least one HTTP client to be created"
    first_call_headers = headers_seen[0]
    assert (
        "Authorization" not in first_call_headers
    ), "Token should NOT be sent for a public repo's initial fetch"
    assert result.get("topics") == ["microscopy"]


@pytest.mark.asyncio
async def test_401_unauthenticated_escalates_to_token(monkeypatch, caplog):
    """If the unauthenticated call gets 401, the token should be tried next."""
    import logging

    extractor = _make_extractor()

    call_count = 0
    auth_header_values: list[str | None] = []

    import httpx

    class _SequencedClient:
        def __init__(self, headers=None, timeout=None):
            self._headers = dict(headers or {})

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, **kwargs):
            nonlocal call_count
            auth_header_values.append(self._headers.get("Authorization"))
            call_count += 1
            if call_count == 1:
                # First call: unauthenticated, returns 401
                return _mock_response(401)
            elif call_count == 2:
                # Second call: with token, returns 200
                return _mock_response(200, {"topics": ["optics"]})
            else:
                # Release endpoint
                return _mock_response(404)

    with patch("httpx.AsyncClient", _SequencedClient):
        with patch.object(
            extractor, "_load_github_token_from_env", return_value="real-token-xyz"
        ):
            with caplog.at_level(
                logging.DEBUG, logger="src.core.generation.platforms.local_git"
            ):
                result = await extractor._fetch_github_supplementary_metadata(
                    "someorg", "private-repo"
                )

    assert call_count >= 2, "Should have retried with token after 401"
    assert auth_header_values[0] is None, "First call must be unauthenticated"
    assert auth_header_values[1] is not None, "Second call must use the token"


@pytest.mark.asyncio
async def test_bad_token_logs_warning_not_raises(caplog):
    """If the token is also rejected (401), a warning should be logged and the
    call should return an empty dict without raising."""
    import logging

    extractor = _make_extractor()

    import httpx

    class _Always401Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, **kwargs):
            return _mock_response(401)

    with patch("httpx.AsyncClient", _Always401Client):
        with patch.object(
            extractor, "_load_github_token_from_env", return_value="expired-token"
        ):
            with caplog.at_level(
                logging.WARNING, logger="src.core.generation.platforms.local_git"
            ):
                result = await extractor._fetch_github_supplementary_metadata(
                    "someorg", "repo"
                )

    assert result == {}, "Should return empty dict when all auth attempts fail"
    warning_messages = [
        r.message for r in caplog.records if r.levelno == logging.WARNING
    ]
    assert any(
        "401" in m for m in warning_messages
    ), "Should log a warning about the rejected token"


@pytest.mark.asyncio
async def test_no_token_no_warning_on_public_200(caplog):
    """With no token and a 200 response, there must be no warnings emitted."""
    import logging

    extractor = _make_extractor()

    class _OkClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, **kwargs):
            if "releases" in url:
                return _mock_response(200, {"tag_name": "v1.0.0"})
            return _mock_response(200, {"topics": ["hardware"]})

    with patch("httpx.AsyncClient", _OkClient):
        with patch.object(extractor, "_load_github_token_from_env", return_value=None):
            with caplog.at_level(
                logging.WARNING, logger="src.core.generation.platforms.local_git"
            ):
                result = await extractor._fetch_github_supplementary_metadata(
                    "openorg", "openrepo"
                )

    warning_text = " ".join(
        r.message for r in caplog.records if r.levelno == logging.WARNING
    )
    assert (
        "401" not in warning_text
    ), "No 401 warning should appear for a clean public repo fetch"
    assert result.get("topics") == ["hardware"]
