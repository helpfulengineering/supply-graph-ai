"""A node's own state is never an object, whatever key asks for it (#530).

The identity model says private keys live "node-local, never in the object store".
Compose broke that without anyone deciding to: it mounts one volume at
`/app/storage`, uses it as the object root, and keeps the identity plane at
`/app/storage/federation`. The local provider lists everything under its root, so
a `--mode migrate` to a cloud provider, or a backup, copied plaintext signing keys
into the destination.

These tests build that layout and try to reach the node's state through the object
API by every route that matters, including the evasions a reservation by name would
miss: `..` segments, an absolute path, and a differently-cased name (macOS and
Windows filesystems are case-insensitive, so `Federation/` *is* `federation/`).

They also pin what must **not** change: a layout that keeps node-local state
outside the object root (the installer's) loses nothing, and neighbours of a
protected path stay ordinary objects. Protection is derived from the node's real
settings, not from reserved key names, so no provider's namespace is taken away.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio

from src.config import settings
from src.core.services.storage_transfer import copy_all_objects
from src.core.storage.base import StorageConfig
from src.core.storage.manager import StorageManager
from src.core.storage.node_local import NodeLocalKeyError
from src.core.storage.providers.local import LocalStorageProvider
from src.core.utils.safe_paths import UnsafePathError

pytestmark = pytest.mark.unit

_KEY_FILE = "federation/identities/did:key:z6MkTEST.json"
_SECRET = '{"private_key": "not-for-a-bucket"}'


def _provider(root: Path) -> LocalStorageProvider:
    return LocalStorageProvider(StorageConfig(provider="local", bucket_name=str(root)))


def _node_state(root: Path, monkeypatch: pytest.MonkeyPatch, *, fed: Path, cfg: Path):
    (fed / "identities").mkdir(parents=True)
    (fed / "identities" / "did:key:z6MkTEST.json").write_text(_SECRET)
    (fed / "identity.json").write_text("{}")
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("{}")
    monkeypatch.setattr(settings, "OHM_FEDERATION_DATA_DIR", str(fed))
    monkeypatch.setenv("OHM_STORAGE_CONFIG_PATH", str(cfg))


@pytest_asyncio.fixture
async def compose_layout(tmp_path, monkeypatch):
    """The Compose layout: the object root is the mount, node state is inside it."""
    root = tmp_path / "storage"
    _node_state(
        root,
        monkeypatch,
        fed=root / "federation",
        cfg=root / "config" / "storage-config.json",
    )
    provider = _provider(root)
    await provider.put_object("okh/d.json", b"{}")
    return root, provider


PROTECTED_KEYS = [
    _KEY_FILE,
    "federation/identity.json",
    "config/storage-config.json",
    "federation",
    # Evasions: none of these may reach what the plain key cannot.
    "okh/../" + _KEY_FILE,
    "./federation/identity.json",
    "federation//identity.json",
    "Federation/identity.json",
    "CONFIG/Storage-Config.json",
]


@pytest.mark.asyncio
async def test_a_full_walk_does_not_see_the_nodes_state(compose_layout) -> None:
    _, provider = compose_layout
    keys = [o["key"] async for o in provider.list_objects()]
    assert keys == ["okh/d.json"], (
        f"a walk of the object store lists node-local state: {keys}. A migrate or "
        "a backup copies whatever it lists."
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("key", PROTECTED_KEYS)
async def test_no_operation_reaches_the_nodes_state(compose_layout, key: str) -> None:
    root, provider = compose_layout

    operations = {
        "get": lambda: provider.get_object(key),
        "put": lambda: provider.put_object(key, b"overwritten"),
        "delete": lambda: provider.delete_object(key),
        "metadata": lambda: provider.get_object_metadata(key),
        "copy from": lambda: provider.copy_object(key, "okh/leak.json"),
        "copy to": lambda: provider.copy_object("okh/d.json", key),
    }
    for name, call in operations.items():
        try:
            await call()
        except NodeLocalKeyError:
            continue
        pytest.fail(f"{name} reached the node's own state through the key {key!r}")

    assert (root / "federation" / "identity.json").read_text() == "{}"
    assert (
        root / "federation" / "identities" / "did:key:z6MkTEST.json"
    ).read_text() == _SECRET
    assert not (root / "okh" / "leak.json").exists()


@pytest.mark.asyncio
async def test_an_absolute_path_cannot_reach_it_either(compose_layout) -> None:
    """`Path("/store") / "/store/federation/x"` is `/store/federation/x`."""
    root, provider = compose_layout
    with pytest.raises(NodeLocalKeyError):
        await provider.get_object(str(root / "federation" / "identity.json"))


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["../outside.json", "okh/../../outside.json"])
async def test_a_key_cannot_leave_the_store(compose_layout, key: str) -> None:
    """The provider used to be `base_path / key` with no containment at all."""
    root, provider = compose_layout
    with pytest.raises(UnsafePathError):
        await provider.put_object(key, b"escaped")
    assert not (root.parent / "outside.json").exists()


@pytest.mark.asyncio
async def test_an_absolute_key_outside_the_store_is_refused(
    compose_layout, tmp_path
) -> None:
    _, provider = compose_layout
    elsewhere = tmp_path / "elsewhere.json"
    with pytest.raises(UnsafePathError):
        await provider.put_object(str(elsewhere), b"escaped")
    assert not elsewhere.exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "key",
    [
        "config/other.json",  # beside the config file: only the file is protected
        "federationx/a.json",  # a name that merely starts the same
        "okh/federation/a.json",  # the name deeper in an ordinary prefix
    ],
)
async def test_neighbours_of_protected_paths_stay_ordinary_objects(
    compose_layout, key: str
) -> None:
    _, provider = compose_layout
    await provider.put_object(key, b"{}")
    assert await provider.get_object(key) == b"{}"
    assert key in [o["key"] async for o in provider.list_objects()]


@pytest.mark.asyncio
async def test_a_layout_with_the_state_outside_the_root_loses_nothing(
    tmp_path, monkeypatch
) -> None:
    """The installer's layout: objects/ beside federation/, not above it."""
    _node_state(
        tmp_path,
        monkeypatch,
        fed=tmp_path / "federation",
        cfg=tmp_path / "config" / "storage-config.json",
    )
    provider = _provider(tmp_path / "objects")

    # Nothing to protect here, so `federation/` is just a name like any other.
    await provider.put_object("federation/a.json", b"{}")
    assert await provider.get_object("federation/a.json") == b"{}"
    assert "federation/a.json" in [o["key"] async for o in provider.list_objects()]


@pytest.mark.asyncio
async def test_a_migrate_does_not_carry_the_nodes_keys_to_the_destination(
    compose_layout, tmp_path
) -> None:
    """The #530 scenario, end to end: what `--mode migrate` actually copies."""
    root, _ = compose_layout
    source = StorageManager(StorageConfig(provider="local", bucket_name=str(root)))
    destination_root = tmp_path / "destination"
    destination = StorageManager(
        StorageConfig(provider="local", bucket_name=str(destination_root))
    )
    await source.connect()
    await destination.connect()

    await copy_all_objects(source, destination)

    copied = sorted(
        str(p.relative_to(destination_root))
        for p in destination_root.rglob("*")
        if p.is_file() and not p.name.endswith(".meta")
    )
    assert copied == ["okh/d.json"], f"a migrate copied: {copied}"
    assert _SECRET not in "".join(
        p.read_text() for p in destination_root.rglob("*") if p.is_file()
    )
