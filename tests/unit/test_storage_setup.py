"""One storage setup, and it has to fail loudly (#372).

Setup was implemented three times and the copies had drifted. The behaviour
worth pinning is not that it creates directories — that part always worked —
but the two things that did not:

- it reported success on a backend it had never reached, because it went
  through ``StorageService.configure``, which swallows connection failures by
  design so the API can boot degraded;
- a second run looked identical to a run that had silently created nothing,
  because only "created" was ever reported.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.services.storage_setup import (
    StorageSetupError,
    setup_storage,
)
from src.core.storage.base import StorageConfig

pytestmark = pytest.mark.asyncio

PREFIXES = {"okh/", "okw/", "packages/", "supply-trees/"}


@pytest.fixture
def local_config(tmp_path):
    return StorageConfig(provider="local", bucket_name=str(tmp_path / "store"))


async def test_first_run_creates_every_prefix(local_config):
    result = await setup_storage(local_config)

    assert result.verified is True
    assert set(result.prefixes_created) == PREFIXES
    assert result.prefixes_found == []
    assert result.initialized is True


async def test_second_run_is_a_no_op_and_says_so(local_config):
    """The distinction a caller needs: nothing to do, versus nothing done."""
    await setup_storage(local_config)
    result = await setup_storage(local_config)

    assert result.verified is True
    assert result.prefixes_created == []
    assert set(result.prefixes_found) == PREFIXES
    assert result.initialized is False


async def test_second_run_does_not_restamp_placeholders(local_config, tmp_path):
    """Re-running must not rewrite placeholders that already exist.

    The standalone script used to, which gave every established directory a new
    `created_at` on each deploy — and under local storage those placeholders
    are files, so a re-run dirtied the working tree.
    """
    await setup_storage(local_config)
    placeholder = tmp_path / "store" / "okh" / ".gitkeep"
    assert placeholder.exists(), "expected a placeholder to have been written"
    before = placeholder.read_bytes()

    await setup_storage(local_config)

    assert placeholder.read_bytes() == before


async def test_unreachable_backend_raises_rather_than_reporting_success():
    """The regression. This used to print a green tick and return normally."""
    config = StorageConfig(provider="local", bucket_name="/dev/null/not-a-directory")

    with pytest.raises(StorageSetupError) as excinfo:
        await setup_storage(config)

    assert "connect" in str(excinfo.value).lower()


async def test_a_backend_that_connects_but_cannot_write_is_not_verified(local_config):
    """Connecting proves a client was built, not that the bucket is writable.

    Credentials that authenticate against a bucket they cannot write to are the
    realistic version of this, and only a round trip catches them.
    """
    manager = MagicMock()
    manager.connect = AsyncMock()
    manager.disconnect = AsyncMock()
    manager.put_object = AsyncMock(side_effect=PermissionError("read-only bucket"))

    with patch("src.core.services.storage_setup.StorageManager", return_value=manager):
        with pytest.raises(StorageSetupError) as excinfo:
            await setup_storage(local_config)

    assert "could not write" in str(excinfo.value).lower()
    manager.disconnect.assert_awaited()


async def test_a_backend_that_returns_different_bytes_is_not_verified(local_config):
    """A write and a read that disagree is not a working backend."""
    manager = MagicMock()
    manager.connect = AsyncMock()
    manager.disconnect = AsyncMock()
    manager.put_object = AsyncMock()
    manager.get_object = AsyncMock(return_value=b"something else entirely")

    with patch("src.core.services.storage_setup.StorageManager", return_value=manager):
        with pytest.raises(StorageSetupError) as excinfo:
            await setup_storage(local_config)

    assert "different content" in str(excinfo.value).lower()


async def test_the_probe_object_is_removed_when_setup_succeeds(local_config, tmp_path):
    """A verified backend is left exactly as it was found."""
    await setup_storage(local_config)

    leftovers = list((tmp_path / "store").rglob("*ohm-setup-probe*"))
    assert leftovers == [], f"probe objects left behind: {leftovers}"
