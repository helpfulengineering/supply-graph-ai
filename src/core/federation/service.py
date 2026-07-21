"""Federation service — identity, peer registry, and lifecycle (MVP foundation)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from src.config import settings
from src.config.security_policy import get_security_policy

from ..services.base import BaseService, ServiceConfig
from ..utils.logging import get_logger
from .catalog import CatalogIndex, build_catalog_index
from .discovery import MdnsAdvertiser, browse_mdns_peers
from .identity import NodeIdentity, load_or_create_identity
from .metrics import FederationMetricsCollector
from .models import PeerState, SyncDigest, SyncDigestResponse, utc_now
from .node_role import (
    NodeCapabilities,
    NodeRole,
    capabilities_for_role,
    parse_node_role,
)
from .peer_registry import PeerRegistry
from .store import FederationStore
from .sync import SyncPeerResult, respond_to_sync_digest, sync_with_peer

if TYPE_CHECKING:
    from ..services.okh_service import OKHService

logger = get_logger(__name__)


class FederationService(BaseService["FederationService"]):
    """
    Manages federation node identity and local peer/follow state.

    Slices 2–4 add catalog build, discovery, and anti-entropy sync.
    """

    def __init__(
        self,
        service_name: str = "FederationService",
        config: Optional[ServiceConfig] = None,
    ) -> None:
        super().__init__(service_name, config)
        self.identity: NodeIdentity | None = None
        self.store: FederationStore | None = None
        self.role: NodeRole = NodeRole.PEER
        self.capabilities: NodeCapabilities = capabilities_for_role(NodeRole.PEER)
        self.data_dir: Path = Path(settings.OHM_FEDERATION_DATA_DIR)
        self._mdns_advertiser: MdnsAdvertiser | None = None
        self._sync_task: asyncio.Task[None] | None = None
        self.federation_metrics = FederationMetricsCollector()

    async def _initialize_dependencies(self) -> None:
        if not settings.OHM_FEDERATION_ENABLED:
            self.logger.info("Federation is disabled (OHM_FEDERATION_ENABLED=false)")
            return

        self.role = parse_node_role(settings.OHM_FEDERATION_NODE_ROLE)
        self.capabilities = capabilities_for_role(self.role)
        self.data_dir = Path(settings.OHM_FEDERATION_DATA_DIR).expanduser()
        self.store = FederationStore(self.data_dir)
        self.identity = load_or_create_identity(
            self.data_dir,
            settings.OHM_FEDERATION_NODE_NAME,
        )
        self.logger.info(
            f"Federation initialized: did={self.identity.did} "
            f"role={self.role.value} data_dir={self.data_dir}"
        )

    async def initialize(self) -> None:
        """Register dependencies on the base service."""
        self.add_dependency("store", self.store)
        self.add_dependency("identity", self.identity)

    @property
    def enabled(self) -> bool:
        return bool(settings.OHM_FEDERATION_ENABLED)

    def require_enabled(self) -> None:
        if not self.enabled:
            raise RuntimeError(
                "Federation is not enabled. Set OHM_FEDERATION_ENABLED=true."
            )

    async def ensure_federation_ready(self) -> None:
        """Ensure service is initialized and federation is enabled."""
        await self.ensure_initialized()
        self.require_enabled()
        if self.identity is None or self.store is None:
            raise RuntimeError("Federation identity or store not loaded")

    def federation_context(self) -> tuple[NodeIdentity, FederationStore]:
        """Return identity and store; call after ``ensure_federation_ready``."""
        if self.identity is None or self.store is None:
            raise RuntimeError("Federation identity or store not loaded")
        return self.identity, self.store

    async def build_catalog_index(self) -> CatalogIndex:
        """Build a signed catalog snapshot from local OKH storage."""
        await self.ensure_federation_ready()
        identity, _store = self.federation_context()
        from ..services.okh_service import OKHService

        okh_service = await OKHService.get_instance()
        return await build_catalog_index(okh_service, identity)

    def list_peers(self) -> list[PeerState]:
        """Return known peers from local store."""
        if self.store is None:
            return []
        return self.store.load_peers()

    async def refresh_peers(
        self,
        *,
        extra_manual_urls: list[str] | None = None,
        mdns_timeout: float = 3.0,
    ) -> list[PeerState]:
        """Discover peers via manual URLs and mDNS, resolve via ``/identify``."""
        await self.ensure_federation_ready()
        identity, store = self.federation_context()

        mdns_peers = []
        if self._mdns_allowed():
            mdns_peers = await asyncio.to_thread(browse_mdns_peers, mdns_timeout)

        registry = PeerRegistry(store)
        return await registry.refresh(
            manual_urls=settings.OHM_FEDERATION_MANUAL_PEERS,
            mdns_peers=mdns_peers,
            local_did=identity.did,
            extra_manual_urls=extra_manual_urls,
        )

    def _mdns_allowed(self) -> bool:
        """mDNS requires env flag, role capability, and SecurityPolicy consent."""
        return (
            settings.OHM_FEDERATION_MDNS_ENABLED
            and self.capabilities.advertise_mdns
            and get_security_policy().mdns_advertise
        )

    def start_mdns(self, port: int) -> None:
        """Advertise this node on the LAN (best-effort)."""
        if not self._mdns_allowed():
            return
        if self.identity is None:
            return
        if self._mdns_advertiser is not None:
            return

        try:
            advertiser = MdnsAdvertiser()
            advertiser.register(
                did=self.identity.did,
                port=port,
                display_name=self.identity.display_name,
            )
            self._mdns_advertiser = advertiser
        except Exception as e:
            logger.warning(f"mDNS advertisement failed (continuing without): {e}")

    def stop_mdns(self) -> None:
        if self._mdns_advertiser:
            self._mdns_advertiser.close()
            self._mdns_advertiser = None

    def follow_peer(self, did: str) -> None:
        """Add a peer DID to the follow allowlist.

        Under shielded ``trust_bootstrap=explicit_only``, mDNS discovery is off
        so follow is never implied by LAN presence — callers must supply a DID
        out of band. The follow API call itself is that explicit step.
        """
        self.require_enabled()
        if self.store is None:
            raise RuntimeError("Federation store not loaded")
        self.store.set_followed(did, True)

    def unfollow_peer(self, did: str) -> None:
        """Remove a peer DID from the follow allowlist."""
        self.require_enabled()
        if self.store is None:
            raise RuntimeError("Federation store not loaded")
        self.store.set_followed(did, False)

    def is_followed(self, did: str) -> bool:
        if self.store is None:
            return False
        return self.store.is_followed(did)

    async def handle_sync_digest(self, digest: SyncDigest) -> SyncDigestResponse:
        """Respond to a peer's anti-entropy digest with missing hashes."""
        await self.ensure_federation_ready()
        if not self.capabilities.can_accept_inbound_sync:
            raise RuntimeError("This node role does not accept inbound sync")
        self.federation_metrics.record_inbound_digest()
        index = await self.build_catalog_index()
        local_hashes = {r.content_hash for r in index.records}
        return respond_to_sync_digest(
            digest,
            local_merkle_root=index.merkle_root,
            local_leaf_hashes=local_hashes,
        )

    def record_sync_result(
        self, result: SyncPeerResult, *, background: bool = False
    ) -> None:
        self.federation_metrics.record_sync_run(
            peer_did=result.peer_did,
            pulled=result.pulled,
            skipped=result.skipped,
            background=background,
            when=utc_now(),
        )

    async def get_status(self) -> dict:
        """Dashboard-friendly federation status snapshot."""
        await self.ensure_federation_ready()
        identity, _store = self.federation_context()
        index = await self.build_catalog_index()
        peers = self.list_peers()
        followed = [p for p in peers if p.followed or self.is_followed(p.did)]
        metrics = self.federation_metrics.snapshot
        return {
            "did": identity.did,
            "display_name": identity.display_name,
            "role": self.role.value,
            "catalog_record_count": index.record_count,
            "merkle_root": index.merkle_root,
            "peer_count": len(peers),
            "followed_peer_count": len(followed),
            "sync_interval_sec": settings.OHM_FEDERATION_SYNC_INTERVAL_SEC,
            "mdns_enabled": self._mdns_allowed(),
            "security_mode": get_security_policy().mode.value,
            "background_sync_running": self._sync_task is not None
            and not self._sync_task.done(),
            "manual_peers": settings.OHM_FEDERATION_MANUAL_PEERS,
            "metrics": metrics,
        }

    async def sync_peer(self, peer: PeerState) -> SyncPeerResult:
        """Run anti-entropy sync against one peer."""
        await self.ensure_federation_ready()
        return await sync_with_peer(self, peer)

    async def sync_with_url(self, peer_url: str) -> SyncPeerResult:
        """Identify a peer URL, ensure it is followed, and sync."""
        await self.ensure_federation_ready()
        identity, store = self.federation_context()

        registry = PeerRegistry(store)
        updated = await registry.refresh(
            manual_urls=[peer_url],
            mdns_peers=[],
            local_did=identity.did,
        )
        if not updated:
            raise RuntimeError(f"Could not identify peer at {peer_url}")
        peer = updated[0]
        if not store.is_followed(peer.did):
            store.set_followed(peer.did, True)
            peer = peer.model_copy(update={"followed": True})
        result = await sync_with_peer(self, peer)
        self.record_sync_result(result)
        return result

    async def sync_all_followed(
        self, *, background: bool = False
    ) -> list[SyncPeerResult]:
        """Sync with every followed peer in the local registry."""
        await self.ensure_federation_ready()
        _identity, store = self.federation_context()
        results: list[SyncPeerResult] = []
        for peer in store.load_peers():
            if peer.followed or store.is_followed(peer.did):
                peer = peer.model_copy(update={"followed": True})
                result = await sync_with_peer(self, peer)
                self.record_sync_result(result, background=background)
                results.append(result)
        return results

    def start_sync_loop(self) -> None:
        """Start periodic background sync for followed peers."""
        if not self.enabled:
            return
        if self._sync_task is not None:
            return
        self._sync_task = asyncio.create_task(self._sync_loop())
        logger.info(
            f"Federation sync loop started (interval={settings.OHM_FEDERATION_SYNC_INTERVAL_SEC}s)"
        )

    async def stop_sync_loop(self) -> None:
        if self._sync_task is None:
            return
        self._sync_task.cancel()
        try:
            await self._sync_task
        except asyncio.CancelledError:
            pass
        self._sync_task = None

    async def _sync_loop(self) -> None:
        interval = max(5, settings.OHM_FEDERATION_SYNC_INTERVAL_SEC)
        while True:
            try:
                await asyncio.sleep(interval)
                if not self.enabled:
                    continue
                await self.ensure_federation_ready()
                results = await self.sync_all_followed(background=True)
                if results:
                    pulled = sum(r.pulled for r in results)
                    if pulled:
                        logger.info(
                            f"Federation background sync stored {pulled} record(s) "
                            f"from {len(results)} peer(s)"
                        )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"Federation background sync failed: {e}")
