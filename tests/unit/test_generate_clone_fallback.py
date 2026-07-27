"""Cloning is the default extraction path, and a failed clone must degrade.

Cloning replaces one HTTP round trip per file with a single compressed transfer
and needs no credential — on a substantial repository that is the difference
between ~20s and exceeding the proxy timeout, and it stops one heavy user
exhausting a shared token's quota for everyone.

Making it the default is only safe if failure degrades. A clone can fail for
reasons that say nothing about the repository: git missing from the image (which
is exactly how this path was silently broken in production), a clone timeout, or
transient network trouble. Those must cost speed, not the request.
"""

from __future__ import annotations

import logging

import pytest

from src.core.api.models.okh.request import OKHGenerateRequest


class TestCloneDefault:
    def test_api_request_clones_by_default(self):
        req = OKHGenerateRequest(url="https://github.com/owner/project")
        assert req.clone is True

    def test_api_path_remains_available_explicitly(self):
        req = OKHGenerateRequest(url="https://github.com/owner/project", clone=False)
        assert req.clone is False


class TestServiceDefault:
    def test_service_signature_defaults_to_clone(self):
        import inspect

        from src.core.services.okh_service import OKHService

        sig = inspect.signature(OKHService.generate_from_url)
        assert sig.parameters["clone"].default is True


class TestCliDefault:
    def test_cli_clones_by_default_and_can_be_disabled(self):
        from src.cli.okh import generate_from_url as cli_generate

        opts = {p.name: p for p in cli_generate.params}
        clone = opts["clone"]
        assert clone.default is True
        # Both spellings must exist, or "--no-clone" in the help is a lie.
        assert "--clone" in clone.opts
        assert "--no-clone" in clone.secondary_opts


@pytest.mark.asyncio
class TestFallback:
    """The behaviour that makes cloning safe to default to."""

    class _Recorder:
        def __init__(self, name, calls, boom=None):
            self.name, self.calls, self.boom = name, calls, boom

        async def extract_project(self, url, persist_path=None):
            self.calls.append(self.name)
            if self.boom:
                raise self.boom
            return f"data-from-{self.name}"

    async def _run(self, clone, boom=None, api=None):
        from src.core.services.okh_service import extract_project_data

        calls: list[str] = []
        result = await extract_project_data(
            url="https://github.com/owner/project",
            clone=clone,
            save_clone=None,
            clone_extractor=self._Recorder("clone", calls, boom),
            api_extractor=api if api is not None else self._Recorder("api", calls),
            logger=logging.getLogger("test"),
        )
        return result, calls

    async def test_clone_is_used_when_it_works(self):
        result, calls = await self._run(clone=True)
        assert calls == ["clone"]
        assert result == "data-from-clone"

    async def test_failed_clone_falls_back_to_the_api_path(self):
        """git missing, a timeout, or network trouble must not fail the request."""
        result, calls = await self._run(
            clone=True, boom=ConnectionError("git: command not found")
        )
        assert calls == ["clone", "api"], "expected a clone attempt, then a fallback"
        assert result == "data-from-api"

    async def test_api_path_is_used_directly_when_cloning_is_off(self):
        result, calls = await self._run(clone=False)
        assert calls == ["api"], "must not attempt a clone when disabled"
        assert result == "data-from-api"

    async def test_no_usable_extractor_still_raises(self):
        """Falling back must not paper over having nowhere to fall back to."""
        from src.core.services.okh_service import extract_project_data

        with pytest.raises(ValueError, match="No API extractor"):
            await extract_project_data(
                url="https://example.com/x",
                clone=False,
                save_clone=None,
                clone_extractor=None,
                api_extractor=None,
                logger=logging.getLogger("test"),
            )

    async def test_clone_failure_with_no_api_extractor_raises(self):
        """The fallback path itself must surface a real failure, not hang or pass."""
        from src.core.services.okh_service import extract_project_data

        calls: list[str] = []
        with pytest.raises(ValueError, match="No API extractor"):
            await extract_project_data(
                url="https://example.com/x",
                clone=True,
                save_clone=None,
                clone_extractor=self._Recorder("clone", calls, RuntimeError("boom")),
                api_extractor=None,
                logger=logging.getLogger("test"),
            )
        assert calls == ["clone"]
