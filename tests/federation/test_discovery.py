"""Unit tests for mDNS discovery helpers."""

from __future__ import annotations

import pytest

from src.core.federation.discovery import (
    OHM_SERVICE_TYPE,
    DiscoveredPeer,
    base_url_from_service,
    parse_txt_properties,
)


@pytest.mark.unit
def test_parse_txt_properties() -> None:
    props = parse_txt_properties(
        {
            "did": b"did:key:z6Mktest",
            "version": b"1.0.0",
        }
    )
    assert props["did"] == "did:key:z6Mktest"
    assert props["version"] == "1.0.0"


@pytest.mark.unit
def test_base_url_from_service() -> None:
    peer = DiscoveredPeer(
        name="node._ohm._tcp.local.",
        host="10.0.0.5",
        port=8001,
        did="did:key:z6Mktest",
        properties={},
    )
    assert base_url_from_service(peer) == "http://10.0.0.5:8001"


@pytest.mark.unit
def test_service_type_constant() -> None:
    assert OHM_SERVICE_TYPE == "_ohm._tcp.local."
