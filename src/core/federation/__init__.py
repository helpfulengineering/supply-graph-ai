"""OHM federation: LAN peer sync, signed OKH catalogs, anti-entropy replication."""

from .identity import NodeIdentity, canonical_json_bytes, load_or_create_identity
from .models import CatalogRecord, NodeInfo, PeerState, SyncDigest
from .node_role import (
    NodeCapabilities,
    NodeRole,
    capabilities_for_role,
    parse_node_role,
)
from .service import FederationService
from .store import FederationStore

__all__ = [
    "CatalogRecord",
    "FederationService",
    "FederationStore",
    "NodeCapabilities",
    "NodeIdentity",
    "NodeInfo",
    "NodeRole",
    "PeerState",
    "SyncDigest",
    "canonical_json_bytes",
    "capabilities_for_role",
    "load_or_create_identity",
    "parse_node_role",
]
