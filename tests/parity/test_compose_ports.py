"""Compose files may not publish a port on every interface undeclared (#523).

A bare host-side port (`"8001:8001"`) binds **0.0.0.0**, not loopback. The
API's own port had this shape in both `docker-compose.yml` (the self-host
artifact) and `docker-compose.federation.yml` (the local federation dev
stack): a node stood up with plain `docker compose up` published its raw,
unauthenticated-by-default (`ENVIRONMENT=development`) API to whatever
network the host is on.

`#341` already gave this treatment to Redis (no host port at all) and
Prometheus (`127.0.0.1:9090:9090`) in `docker-compose.yml`, and
`#480`/`test_installer_ports.py` gave it to the installer's own `docker run`.
The API's port in both compose files was the one gap neither covered.

Like the installer's gate, this does not forbid publishing wide. It forbids
**undeclared** publishing: every port bound to all interfaces needs a row
below saying why, which forces the question to be answered once, in writing.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMPOSE_FILES = ("docker-compose.yml", "docker-compose.federation.yml")

#: A host-side bind that is not reachable from off the machine.
_LOOPBACK = ("127.0.0.1", "localhost", "::1")

#: (file, container port) -> why this one is published on every interface.
#: A row is a decision, not a formality.
PUBLISHED_ON_ALL_INTERFACES = {
    ("docker-compose.yml", "8080"): (
        "The web interface is the product: a node nobody can open is not a "
        "node. It is also the only surface with a login, and it proxies /v1 "
        "itself, which is what lets the API stay on loopback."
    ),
}


def _binds_all_interfaces(spec: str) -> bool:
    """True when the host side names no interface, or names a routable one.

    ``HOST:CONTAINER`` has no host interface and so binds every one of them;
    ``IFACE:HOST:CONTAINER`` binds what it names.
    """
    parts = str(spec).split(":")
    if len(parts) < 3:
        return True
    return parts[0] not in _LOOPBACK and not parts[0].startswith("${")


def _container_port(spec: str) -> str:
    """The last field of a port spec is always the container port."""
    return str(spec).rsplit(":", 1)[-1]


def _port_specs(compose_file: str) -> list[str]:
    doc = yaml.safe_load((_REPO_ROOT / compose_file).read_text())
    specs: list[str] = []
    for service in doc.get("services", {}).values():
        specs.extend(service.get("ports") or [])
    return specs


@pytest.mark.parametrize("compose_file", _COMPOSE_FILES)
def test_compose_publishes_nothing_undeclared(compose_file: str) -> None:
    specs = _port_specs(compose_file)
    assert (
        specs
    ), f"No port publications found in {compose_file}; has its shape changed?"

    offenders = {
        _container_port(spec): spec
        for spec in specs
        if _binds_all_interfaces(spec)
        and (compose_file, _container_port(spec)) not in PUBLISHED_ON_ALL_INTERFACES
    }
    assert not offenders, (
        f"These ports in {compose_file} are published on every interface and "
        "undeclared.\nBind them to 127.0.0.1, or add a row saying why they "
        "must be wide:\n"
        + "\n".join(f"    {spec}" for spec in sorted(offenders.values()))
    )


def test_the_api_port_is_bound_to_an_interface_in_every_compose_file() -> None:
    """The API's own bind is variable-driven, so an operator can override it —
    same shape as the installer's ``OHM_API_BIND``."""
    for compose_file in _COMPOSE_FILES:
        text = (_REPO_ROOT / compose_file).read_text()
        assert "${API_BIND:-127.0.0.1}" in text, (
            f"{compose_file}: the API bind address should default to loopback "
            "via API_BIND, so overriding it is a deliberate documented act."
        )
