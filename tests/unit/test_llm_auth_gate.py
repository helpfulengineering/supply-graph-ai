"""Authentication is required only when a request would genuinely spend.

The gate used to key off the request's *intent* — the `no_llm` flag — rather
than on whether an LLM was actually available. The web UI always requests
LLM-enabled generation, so switching the setting on would have rejected every
generation in order to guard a cost that could not occur. That is why it stayed
off, and why the spend path stayed unguarded.

Fixing the semantics is what makes arming the flag safe, which is why both ship
together: separated, merging one without the other rejects every generation.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.core.api.routes.okh import _enforce_llm_auth_if_required
from src.core.llm.availability import LLMAvailability, LLMUnavailableReason

pytestmark = pytest.mark.unit

_USER = object()  # any authenticated principal


def _availability(available: bool):
    value = (
        LLMAvailability(available=True, provider="anthropic", source="credential_store")
        if available
        else LLMAvailability.unavailable(LLMUnavailableReason.NOT_CONFIGURED)
    )
    return patch(
        "src.core.llm.availability.resolve_llm_availability",
        AsyncMock(return_value=value),
    )


def _flag(enabled: bool):
    from src.config.schema import Settings

    return patch(
        "src.config.schema.get_settings",
        return_value=Settings(generate_from_url_require_auth_for_llm=enabled),
    )


# --- The bug: gating on intent rather than on spend --------------------------


@pytest.mark.asyncio
async def test_anonymous_generation_is_allowed_when_no_provider_is_configured():
    """THE fix. The UI always asks for LLM, so the old gate would have rejected
    every generation to protect a cost that cannot occur."""
    with _flag(True), _availability(False):
        await _enforce_llm_auth_if_required(no_llm=False, user=None)  # must not raise


@pytest.mark.asyncio
async def test_anonymous_generation_is_refused_once_a_provider_exists():
    with _flag(True), _availability(True):
        with pytest.raises(HTTPException) as raised:
            await _enforce_llm_auth_if_required(no_llm=False, user=None)

    assert raised.value.status_code == 401
    assert "no_llm=true" in str(raised.value.detail)


@pytest.mark.asyncio
async def test_an_authenticated_caller_proceeds():
    with _flag(True), _availability(True):
        await _enforce_llm_auth_if_required(no_llm=False, user=_USER)


# --- Things that must never be gated -----------------------------------------


@pytest.mark.asyncio
async def test_opting_out_of_the_llm_is_never_refused():
    """A heuristic-only request spends nothing, whoever asks for it."""
    with _flag(True), _availability(True):
        await _enforce_llm_auth_if_required(no_llm=True, user=None)


@pytest.mark.asyncio
async def test_the_flag_off_gates_nothing():
    with _flag(False), _availability(True):
        await _enforce_llm_auth_if_required(no_llm=False, user=None)


@pytest.mark.asyncio
async def test_availability_is_not_resolved_when_it_cannot_change_the_answer():
    """An authenticated caller, an opt-out, or the flag off all short-circuit —
    each avoids a credential-store read on a request that cannot be refused."""
    for no_llm, user, flag in (
        (True, None, True),
        (False, _USER, True),
        (False, None, False),
    ):
        resolver = AsyncMock()
        with (
            _flag(flag),
            patch("src.core.llm.availability.resolve_llm_availability", resolver),
        ):
            await _enforce_llm_auth_if_required(no_llm=no_llm, user=user)
        resolver.assert_not_awaited()


# --- Armed in production, and safe to be ------------------------------------


def test_production_arms_the_flag():
    """Inert until a provider exists, protective the moment one does — which
    removes the step someone would otherwise have to remember at exactly the
    wrong moment."""
    from src.config.schema import deploy_env_vars

    assert deploy_env_vars("production")["GENERATE_FROM_URL_REQUIRE_AUTH_FOR_LLM"] == (
        "True"
    )


# --- Through the actual routes -----------------------------------------------
#
# The checks above exercise the gate directly. These drive the real endpoints,
# because "is the gate wired into both of them" is not something a unit test of
# the gate can answer.


def _app():
    from fastapi import FastAPI

    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app


async def _post(path: str, body: dict):
    """POST a route with everything AFTER the gate stubbed out.

    The gate is the subject; whether Celery can reach a broker or the extractor
    can reach GitHub is not, and letting either run would make this a network
    test that fails for reasons unrelated to authentication.
    """
    import httpx

    enqueued = MagicMock()
    enqueued.id = "job-1"

    with (
        patch(
            "src.core.jobs.generation_jobs.generate_from_url_task.delay",
            return_value=enqueued,
        ),
        patch(
            "src.core.services.okh_service.OKHService.generate_from_url",
            AsyncMock(
                return_value={"success": True, "manifest": {}, "quality_report": {}}
            ),
        ),
    ):
        transport = httpx.ASGITransport(app=_app())
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.post(path, json=body)


_LLM_REQUEST = {"urls": ["https://github.com/octocat/Hello-World"], "no_llm": False}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/v1/api/okh/generate-from-url/jobs",
        "/v1/api/okh/generate-from-url",
    ],
)
async def test_both_routes_refuse_anonymous_llm_generation_when_a_provider_exists(
    path, monkeypatch
):
    monkeypatch.setenv("GENERATE_FROM_URL_REQUIRE_AUTH_FOR_LLM", "true")
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("JOB_BROKER_URL", "memory://")

    body = (
        _LLM_REQUEST
        if "jobs" in path
        else {**_LLM_REQUEST, "url": _LLM_REQUEST["urls"][0]}
    )
    with _availability(True):
        response = await _post(path, body)

    assert response.status_code == 401, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/v1/api/okh/generate-from-url/jobs",
        "/v1/api/okh/generate-from-url",
    ],
)
async def test_both_routes_allow_anonymous_generation_with_no_provider(
    path, monkeypatch
):
    """The armed flag must be inert until a credential exists, or production
    rejects every generation the moment this ships."""
    monkeypatch.setenv("GENERATE_FROM_URL_REQUIRE_AUTH_FOR_LLM", "true")
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("JOB_BROKER_URL", "memory://")

    body = (
        _LLM_REQUEST
        if "jobs" in path
        else {**_LLM_REQUEST, "url": _LLM_REQUEST["urls"][0]}
    )
    with _availability(False):
        response = await _post(path, body)

    assert response.status_code != 401, response.text
