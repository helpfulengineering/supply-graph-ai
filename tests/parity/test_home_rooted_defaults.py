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
the exception, it forbids the **undeclared** one. `KNOWN_GAPS` is the ratchet's
backlog: the change that closes a gap deletes its row, and a row that has stopped
being true fails, so the list cannot go stale.

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

#: (env var, compose file) pairs the compose files do not yet set, and why.
#: Delete a row when the gap closes — a row that is no longer true fails.
_STORAGE_CONFIG_GAP = (
    "Saving storage settings from the UI writes to ~/.ohm/storage-config.json, "
    "which does not exist in the container, so the save fails with a clear "
    "error. The installer avoids it by keeping the config outside the object "
    "root (/app/storage/config vs /app/storage/objects). Compose cannot do the "
    "same without moving existing data: its object root IS /app/storage, so a "
    "config file there would be listed, served and erased as an object of the "
    "bucket it configures. Needs a decision on where the file lives."
)
KNOWN_GAPS = {
    ("OHM_STORAGE_CONFIG_PATH", "docker-compose.yml"): _STORAGE_CONFIG_GAP,
    ("OHM_STORAGE_CONFIG_PATH", "docker-compose.federation.yml"): _STORAGE_CONFIG_GAP,
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
        if (env, compose_file) not in KNOWN_GAPS
    ],
)
def test_compose_sets_every_override(env: str, compose_file: str, service: str) -> None:
    assert env in _compose_env(compose_file, service), (
        f"{compose_file} service {service} does not set {env}. Set it to a path "
        "on the service's storage volume, or record the gap in KNOWN_GAPS."
    )


@pytest.mark.parametrize("env,compose_file", sorted(KNOWN_GAPS))
def test_known_gaps_are_still_gaps(env: str, compose_file: str) -> None:
    """A gap that has closed must have its row deleted, or the list rots."""
    still_missing = [
        service
        for service in COMPOSE_API_SERVICES[compose_file]
        if env not in _compose_env(compose_file, service)
    ]
    assert still_missing, (
        f"{compose_file} now sets {env} on every API service. "
        "Delete its row from KNOWN_GAPS."
    )
