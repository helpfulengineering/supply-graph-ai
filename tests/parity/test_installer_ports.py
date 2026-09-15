"""The installer may not publish a port on every interface undeclared (#480).

`docker run -p 8001:8001` binds **0.0.0.0**, not loopback. `scripts/install.sh`
published the API that way, so a node installed on a laptop joining a cafe
network exposed its raw API to that network — an API whose write surface is
still being closed (#481). The browser never used that port: the web container
reverse-proxies `/v1` over the container network, which is why publishing it
wide served direct API use and debugging only.

`#341` already gave `docker-compose.yml` this treatment — Redis lost its host
port mapping entirely and Prometheus became `127.0.0.1:9090:9090` — and
`test_compose_defaults.py` guards that file. The installer had no equivalent,
which is how it was left behind. This is that equivalent, and it exists mostly
for the *next* service: the runtime-federation work adds Redis and a Celery
worker to this script, and Redis must not acquire a host port on the way in.

Like the compose gate, it does not forbid publishing wide. It forbids
**undeclared** publishing: every port bound to all interfaces needs a row below
saying why, which forces the question to be answered once, in writing.

**Known limit.** A host interface written as a shell variable is taken on
trust — resolving it would mean interpreting the script. So a future
`-p "${SOMETHING}:1234:1234"` passes this gate whatever `SOMETHING` defaults
to. The API's own default is pinned by the second test instead; a new
variable-driven bind would want the same treatment.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_INSTALLER = Path(__file__).resolve().parents[2] / "scripts" / "install.sh"

#: `-p` arguments that are port mappings, as written in the script.
#:
#: The trailing `:<digits>` is load-bearing: this script also runs
#: `mkdir -p "$DATA_DIR"`, and a looser pattern reports that as a published
#: port. Every Docker publication ends in a literal container port.
_PUBLISH = re.compile(r'-p\s+"(?P<spec>[^"]*:\d+)"')

#: A host-side bind that is not reachable from off the machine.
_LOOPBACK = ("127.0.0.1", "localhost", "::1")

#: Container port -> why this one is published on every interface.
#: A row is a decision, not a formality.
PUBLISHED_ON_ALL_INTERFACES = {
    "8080": (
        "The web interface is the product: a node nobody can open is not a "
        "node. It is also the only surface with a login, and it proxies /v1 "
        "itself, which is what lets the API stay on loopback."
    ),
}


def _container_port(spec: str) -> str:
    """The last field of a `-p` spec is always the container port."""
    return spec.rsplit(":", 1)[-1]


def _binds_all_interfaces(spec: str) -> bool:
    """True when the host side names no interface, or names a routable one.

    `HOST:CONTAINER` has no host interface and so binds every one of them;
    `IFACE:HOST:CONTAINER` binds what it names.
    """
    parts = spec.split(":")
    if len(parts) < 3:
        return True
    return parts[0] not in _LOOPBACK and not parts[0].startswith("${")


def test_installer_publishes_nothing_undeclared() -> None:
    text = _INSTALLER.read_text()
    specs = [m.group("spec") for m in _PUBLISH.finditer(text)]
    assert specs, "No -p publications found; has the installer's shape changed?"

    offenders = {
        _container_port(spec): spec
        for spec in specs
        if _binds_all_interfaces(spec)
        and _container_port(spec) not in PUBLISHED_ON_ALL_INTERFACES
    }
    assert not offenders, (
        "These installer ports are published on every interface and undeclared.\n"
        "Bind them to 127.0.0.1, or add a row saying why they must be wide:\n"
        + "\n".join(f"    -p {spec}" for spec in sorted(offenders.values()))
    )


def test_the_api_port_is_bound_to_an_interface() -> None:
    """The API's own bind is variable-driven, so an operator can override it."""
    text = _INSTALLER.read_text()
    assert 'API_BIND="${OHM_API_BIND:-127.0.0.1}"' in text, (
        "The API bind address should default to loopback via OHM_API_BIND, "
        "so overriding it is a deliberate documented act."
    )
    assert (
        '-p "${API_BIND}:${API_PORT}:8001"' in text
    ), "The API port should be published through API_BIND, not bare."
