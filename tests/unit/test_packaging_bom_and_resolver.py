"""Regression: BOM fallback when external_file 404s; FileResolver session reuse."""

from __future__ import annotations

import pytest

from src.core.models.package import DownloadOptions
from src.core.packaging.builder import _bom_inline_fallback_payload
from src.core.packaging.file_resolver import FileResolver


def test_bom_inline_fallback_payload_from_components() -> None:
    bom = {"external_file": "bom/bom.json", "components": [{"sku": "x"}]}
    assert _bom_inline_fallback_payload(bom) == {"components": [{"sku": "x"}]}


def test_bom_inline_fallback_payload_only_external_file() -> None:
    assert _bom_inline_fallback_payload({"external_file": "bom/bom.json"}) is None


@pytest.mark.asyncio
async def test_file_resolver_session_reopened_after_context() -> None:
    fr = FileResolver()
    async with fr:
        assert fr.session is not None
        assert not fr.session.closed
    assert fr.session is None

    async with fr:
        assert fr.session is not None
        assert not fr.session.closed
    assert fr.session is None


def test_file_resolver_max_retries_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OHM_PACKAGE_FETCH_MAX_RETRIES", "0")
    fr = FileResolver()
    assert fr.download_options.max_retries == 0


def test_file_resolver_max_retries_env_invalid_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OHM_PACKAGE_FETCH_MAX_RETRIES", "bogus")
    fr = FileResolver()
    assert fr.download_options.max_retries == 3


def test_file_resolver_max_retries_clamped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OHM_PACKAGE_FETCH_MAX_RETRIES", "99")
    fr = FileResolver()
    assert fr.download_options.max_retries == 10


def test_file_resolver_explicit_options_ignore_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OHM_PACKAGE_FETCH_MAX_RETRIES", "0")
    fr = FileResolver(DownloadOptions(max_retries=5))
    assert fr.download_options.max_retries == 5
