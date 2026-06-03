"""Unit tests for federation node roles."""

from __future__ import annotations

import pytest

from src.core.federation.node_role import (
    NodeRole,
    capabilities_for_role,
    parse_node_role,
)


@pytest.mark.unit
def test_parse_node_role_defaults_to_peer() -> None:
    assert parse_node_role("") == NodeRole.PEER


@pytest.mark.unit
def test_peer_capabilities() -> None:
    caps = capabilities_for_role(NodeRole.PEER)
    assert caps.can_accept_inbound_sync is True
    assert caps.must_use_relay is False
    assert caps.expose_federation_api is True


@pytest.mark.unit
def test_edge_capabilities() -> None:
    caps = capabilities_for_role(NodeRole.EDGE)
    assert caps.can_accept_inbound_sync is False
    assert caps.must_use_relay is True
    assert caps.expose_federation_api is False


@pytest.mark.unit
def test_invalid_role_raises() -> None:
    with pytest.raises(ValueError, match="Invalid OHM_FEDERATION_NODE_ROLE"):
        parse_node_role("invalid")
