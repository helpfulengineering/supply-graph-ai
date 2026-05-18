"""Federation service — identity, peer registry, and lifecycle (MVP foundation)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.config import settings

from ..services.base import BaseService, ServiceConfig
from ..utils.logging import get_logger
from .identity import NodeIdentity, load_or_create_identity
from .node_role import (
    NodeCapabilities,
    NodeRole,
    capabilities_for_role,
    parse_node_role,
)
from .store import FederationStore

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
