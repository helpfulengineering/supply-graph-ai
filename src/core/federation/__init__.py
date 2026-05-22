"""OHM federation: LAN peer sync, signed OKH catalogs, anti-entropy replication."""

from .catalog import CatalogIndex, build_catalog_index, manifest_content_hash
from .identity import NodeIdentity, canonical_json_bytes, load_or_create_identity
from .merkle import merkle_root
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
    "CatalogIndex",
    "CatalogRecord",
    "FederationService",
    "FederationStore",
    "NodeCapabilities",
    "NodeIdentity",
    "NodeInfo",
    "NodeRole",
    "PeerState",
    "SyncDigest",
    "build_catalog_index",
    "canonical_json_bytes",
    "capabilities_for_role",
    "load_or_create_identity",
    "manifest_content_hash",
    "merkle_root",
    "parse_node_role",
]
