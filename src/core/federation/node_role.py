"""Federation node roles and capability flags (MVP: peer only)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NodeRole(str, Enum):
    """OHM federation deployment role."""

    PEER = "peer"
    EDGE = "edge"
    RELAY = "relay"
    REGISTRY = "registry"


@dataclass(frozen=True)
class NodeCapabilities:
    """What this node instance is allowed to do."""

    role: NodeRole
    can_accept_inbound_sync: bool
    must_use_relay: bool
    advertise_mdns: bool
    expose_federation_api: bool


def capabilities_for_role(role: NodeRole) -> NodeCapabilities:
    """Return capability flags for a role (v0.2 fills in edge/relay/registry)."""
    if role == NodeRole.PEER:
        return NodeCapabilities(
            role=role,
            can_accept_inbound_sync=True,
            must_use_relay=False,
            advertise_mdns=True,
            expose_federation_api=True,
        )
    if role == NodeRole.EDGE:
        return NodeCapabilities(
            role=role,
            can_accept_inbound_sync=False,
            must_use_relay=True,
            advertise_mdns=True,
            expose_federation_api=False,
        )
    if role == NodeRole.RELAY:
        return NodeCapabilities(
            role=role,
            can_accept_inbound_sync=True,
            must_use_relay=False,
            advertise_mdns=False,
            expose_federation_api=True,
        )
    if role == NodeRole.REGISTRY:
        return NodeCapabilities(
            role=role,
            can_accept_inbound_sync=False,
            must_use_relay=False,
            advertise_mdns=False,
            expose_federation_api=True,
        )
    raise ValueError(f"Unknown role: {role}")


def parse_node_role(value: str) -> NodeRole:
    """Parse role from config string."""
    normalized = (value or "peer").strip().lower()
    try:
        return NodeRole(normalized)
    except ValueError as exc:
        valid = ", ".join(r.value for r in NodeRole)
        raise ValueError(
            f"Invalid OHM_FEDERATION_NODE_ROLE '{value}'; expected {valid}"
        ) from exc
