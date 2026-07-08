"""Base class for HTTP production probes."""

from __future__ import annotations

from harness.base import BaseLoopModule
from harness.config import HarnessConfig, ModuleConfig
from harness.probes.http import check_api_reachable
from harness.protocol import Inventory, LoopReport, LoopStatus, Observations


class ProbeModule(BaseLoopModule):
    """Probe that skips when the API health endpoint is unreachable."""

    status = LoopStatus.ONLINE

    def __init__(
        self,
        config: HarnessConfig,
        module_config: ModuleConfig | None = None,
    ) -> None:
        super().__init__(config, module_config)

    def _skip_if_unreachable(self) -> bool:
        return bool(self.module_config.options.get("skip_if_unreachable", True))

    def _api_path_prefix(self) -> str:
        return self.config.api_path_prefix

    def run(self) -> LoopReport:
        if not self.module_config.enabled:
            return LoopReport(
                module=self.name,
                status=LoopStatus.SKIPPED,
                summary=f"{self.name} disabled in config",
            )

        inventory = self.discover()
        if self._skip_if_unreachable() and not check_api_reachable(
            self.config.api_health_url
        ):
            return LoopReport(
                module=self.name,
                status=LoopStatus.SKIPPED,
                inventory=inventory,
                summary=(
                    f"{self.name}: skipped (API unreachable at "
                    f"{self.config.api_health_url})"
                ),
                observations=Observations(
                    data={"skipped": True, "reason": "api_unreachable"},
                ),
            )

        return super().run()
