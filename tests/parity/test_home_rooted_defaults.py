"""A default rooted at `$HOME` must be overridden wherever the app runs in a container.

The image runs as an unprivileged `ohm` user created with `useradd -r`, which
gives it no home directory. Anything the server writes under `Path.home()` then
either fails with `PermissionError: /home/ohm`, or — worse — lands inside the
container, off every mount, and is destroyed on the first upgrade.

Both happened on a clean install of 0.12.2. The identity key store defaults to
`~/.ohm/federation`; `install.sh` never set `OHM_FEDERATION_DATA_DIR`; so minting
an identity returned a 500. The workaround, `mkdir /home/ohm`, made it worse: the
keys then lived in the container while the space claim, which they sign for,
persisted to the mount, leaving a claim whose admin could never sign again.
Compose had the override and the installer did not, and nothing compared them.

So this asks the question at the source rather than at the deployment file:

1. Every `Path.home()` call in server code must be declared below — what setting
   overrides it, or why it needs none. A new one fails here first.
2. Every declared override must be set by the installer and by the compose files.

Like `test_compose_defaults.py` and `test_installer_ports.py`, it does not forbid
the exception, it forbids the **undeclared** one.

3. The image's own default agrees with its entrypoint, so a bare `docker run` and
   any deployment file that forgets are still correct.
4. In every compose layout the node's state is *unreachable through the object
   store*. Compose uses one volume as the object root and keeps the identity plane
   inside it, so a full walk (migrate, backup) used to copy plaintext signing keys
   into the destination (#530). The storage layer now refuses them; this proves it
   for each compose file's real paths rather than for a hand-built example.

`expanduser` is deliberately not scanned. It expands a *caller-supplied* path,
which is a different (and separately sandboxed) concern; only a default the
server chooses for itself belongs here.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import NamedTuple, Optional

import pytest
import yaml

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]
_INSTALLER = _ROOT / "scripts" / "install.sh"

#: The CLI runs on the operator's own machine, where a home directory exists.
_SERVER_SOURCE = _ROOT / "src"
_EXCLUDED = (_ROOT / "src" / "cli",)


class HomeDefault(NamedTuple):
    #: The environment variable that overrides it, or None when none is needed.
    env: Optional[str]
    #: Why this is safe (env is None) or what the override points at.
    note: str


#: Server files that call `Path.home()`, and what makes each safe in a container.
HOME_ROOTED = {
    "src/config/settings.py": HomeDefault(
        "OHM_FEDERATION_DATA_DIR",
        "identity keys, node identity, peer/follow state; must sit on the mount",
    ),
    "src/core/services/storage_config_store.py": HomeDefault(
        "OHM_STORAGE_CONFIG_PATH",
        "the storage settings saved from the UI; must sit on the mount",
    ),
    "src/core/generation/platforms/github.py": HomeDefault(
        None, "cache only; falls back to the temp dir when there is no home"
    ),
    "src/core/generation/platforms/gitlab.py": HomeDefault(
        None, "cache only; falls back to the temp dir when there is no home"
    ),
}

#: Compose file -> the services that run the API process. `ohm-worker` is
#: absent on purpose: `src/core/jobs` has no identity, federation or auth code,
#: so it never reads the identity plane.
COMPOSE_API_SERVICES = {
    "docker-compose.yml": ("ohm-api",),
    "docker-compose.federation.yml": (
        "ohm-peer-a",
        "ohm-peer-b",
        "ohm-edge",
        "ohm-relay",
    ),
}


def _relative(path: Path) -> str:
    return path.relative_to(_ROOT).as_posix()


def _files_calling_path_home() -> set[str]:
    """Server files with a `Path.home()` call, found in the syntax tree.

    Not a text search: `github.py` mentions `Path.home()` in a comment, and a
    grep would report a call that does not exist.
    """
    found: set[str] = set()
    for path in _SERVER_SOURCE.rglob("*.py"):
        if any(excluded in path.parents for excluded in _EXCLUDED):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "home"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "Path"
            ):
                found.add(_relative(path))
                break
    return found


def _compose_env(compose_file: str, service: str) -> set[str]:
    """Variables a service sets in its own `environment:` block.

    Values arriving through `env_file` are invisible here, which is the point:
    they are a self-hoster's `.env`, not something the repo ships.
    """
    services = yaml.safe_load((_ROOT / compose_file).read_text("utf-8"))["services"]
    env = services[service].get("environment") or []
    if isinstance(env, dict):
        return set(env)
    return {entry.split("=", 1)[0] for entry in env}


def _overrides() -> list[str]:
    return sorted({d.env for d in HOME_ROOTED.values() if d.env})


def test_every_home_rooted_default_is_declared() -> None:
    found = _files_calling_path_home()
    declared = set(HOME_ROOTED)

    undeclared = sorted(found - declared)
    assert not undeclared, (
        "These server files default to a path under $HOME, which the container "
        "user does not have:\n"
        + "\n".join(f"    {f}" for f in undeclared)
        + "\nDeclare each in HOME_ROOTED with the env var that overrides it "
        "(and set that in install.sh and the compose files), or say why it is "
        "safe. Otherwise it writes into the container and loses it on upgrade."
    )
    stale = sorted(declared - found)
    assert not stale, (
        f"HOME_ROOTED names files that no longer call Path.home(): {stale}. "
        "Delete the rows."
    )


@pytest.mark.parametrize("env", _overrides())
def test_the_installer_sets_every_override(env: str) -> None:
    text = _INSTALLER.read_text(encoding="utf-8")
    assert re.search(rf'-e\s+"{env}=', text), (
        f"scripts/install.sh does not set {env}. Left at its default it resolves "
        "under the container user's home, which the image never creates: the "
        "first write fails, or lands off the mount and dies on upgrade."
    )


@pytest.mark.parametrize(
    "env,compose_file,service",
    [
        (env, compose_file, service)
        for env in _overrides()
        for compose_file, services in COMPOSE_API_SERVICES.items()
        for service in services
    ],
)
def test_compose_sets_every_override(env: str, compose_file: str, service: str) -> None:
    assert env in _compose_env(compose_file, service), (
        f"{compose_file} service {service} does not set {env}. Set it to a path "
        "on the service's storage volume."
    )


def test_the_image_default_agrees_with_its_entrypoint() -> None:
    """The entrypoint creates and chowns one path; the image must default to it.

    The application's own default is under the user's home. The entrypoint
    already assumed `/app/storage/federation`, so the two disagreed and every
    deployment file had to paper over it — which is how the installer shipped
    without it.
    """
    dockerfile = (_ROOT / "Dockerfile").read_text(encoding="utf-8")
    entrypoint = (_ROOT / "deploy" / "docker" / "docker-entrypoint.sh").read_text(
        encoding="utf-8"
    )

    image = re.search(r"^ENV\s+OHM_FEDERATION_DATA_DIR=(\S+)", dockerfile, re.M)
    assumed = re.search(r"\$\{OHM_FEDERATION_DATA_DIR:-([^}]+)\}", entrypoint)

    assert image, "the Dockerfile does not set OHM_FEDERATION_DATA_DIR"
    assert assumed, "the entrypoint no longer names a default identity directory"
    assert image.group(1) == assumed.group(1), (
        f"the image defaults to {image.group(1)} but its entrypoint prepares "
        f"{assumed.group(1)}"
    )


@pytest.mark.parametrize("env", _overrides())
def test_the_image_sets_a_default_for_every_override(env: str) -> None:
    """A bare `docker run` — no installer, no compose — must not fall back to $HOME.

    The two tests above prove install.sh and the compose files each set every
    declared override; neither protects a bare `docker run` that skips both, which
    is exactly what CI's own "Test Docker Image" job does. Only
    `OHM_FEDERATION_DATA_DIR` had a Dockerfile `ENV` default before this test
    existed (`test_the_image_default_agrees_with_its_entrypoint`, above) — nothing
    required *every* declared override to have one, so a second `HOME_ROOTED`
    entry (`OHM_STORAGE_CONFIG_PATH`, for #544's liveness marker) shipped without
    it and crashed the API on boot with `PermissionError: /home/ohm` the first
    time anything tried to write there. That test stays as the stricter check for
    the one path the entrypoint also pre-creates and chowns; this is the general
    one every declared override must pass.
    """
    dockerfile = (_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(rf"^ENV\s+{env}=\S+", dockerfile, re.M), (
        f"the Dockerfile does not set a default for {env}. Without one, a bare "
        "`docker run` (no installer, no compose) falls back to a path under "
        "$HOME, which this image's user cannot write to."
    )


_DEFAULT = re.compile(r"^\$\{[A-Z_]+:-(?P<default>.*)\}$")


def _compose_settings(compose_file: str, service: str) -> dict[str, str]:
    """A service's `environment:` as {name: value}, with `${X:-default}` resolved."""
    services = yaml.safe_load((_ROOT / compose_file).read_text("utf-8"))["services"]
    env = services[service].get("environment") or []
    pairs = env.items() if isinstance(env, dict) else (e.split("=", 1) for e in env)
    settings_ = {}
    for name, value in pairs:
        value = str(value)
        match = _DEFAULT.match(value)
        settings_[name] = match.group("default") if match else value
    return settings_


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "compose_file,service",
    [(f, svc) for f, services in COMPOSE_API_SERVICES.items() for svc in services],
)
async def test_the_nodes_state_is_unreachable_through_the_object_store(
    compose_file: str, service: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Build this service's real layout and walk its object store.

    The container paths are mapped onto a temp directory, the node's identity and
    saved configuration are written where the compose file says they go, and the
    object store is pointed where the compose file points it. Whatever the compose
    file arranges, a walk must find only real objects and no key may reach the
    node's state.
    """
    from src.config import settings
    from src.core.storage.base import StorageConfig
    from src.core.storage.node_local import NodeLocalKeyError
    from src.core.storage.providers.local import LocalStorageProvider

    env = _compose_settings(compose_file, service)
    mount = "/app/storage"

    def on_disk(container_path: str) -> Path:
        # Relative paths resolve against the image's WORKDIR, /app.
        absolute = (
            container_path
            if container_path.startswith("/")
            else f"/app/{container_path}"
        )
        assert absolute == mount or absolute.startswith(mount + "/"), (
            f"{compose_file}:{service} puts {container_path} outside the storage "
            f"mount {mount}; extend this test to model where it lives"
        )
        return tmp_path / absolute.removeprefix(mount).lstrip("/")

    root = on_disk(env["LOCAL_STORAGE_PATH"])
    fed = on_disk(env["OHM_FEDERATION_DATA_DIR"])
    cfg = on_disk(env["OHM_STORAGE_CONFIG_PATH"])

    (fed / "identities").mkdir(parents=True)
    (fed / "identities" / "did:key:z6MkTEST.json").write_text('{"private_key": "x"}')
    (fed / "identity.json").write_text("{}")
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("{}")
    monkeypatch.setattr(settings, "OHM_FEDERATION_DATA_DIR", str(fed))
    monkeypatch.setenv("OHM_STORAGE_CONFIG_PATH", str(cfg))

    provider = LocalStorageProvider(
        StorageConfig(provider="local", bucket_name=str(root))
    )
    await provider.put_object("okh/d.json", b"{}")

    keys = [o["key"] async for o in provider.list_objects()]
    assert keys == ["okh/d.json"], (
        f"{compose_file}:{service} lists node-local state as objects: {keys}. "
        "A migrate or backup would copy identity keys into the destination."
    )
    for state in (fed / "identity.json", cfg):
        key = state.relative_to(root).as_posix() if root in state.parents else None
        if key is not None:  # state outside the object root has nothing to reach
            with pytest.raises(NodeLocalKeyError):
                await provider.get_object(key)
