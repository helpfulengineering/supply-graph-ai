"""LAN discovery via mDNS/DNS-SD (zeroconf) for OHM federation peers."""

from __future__ import annotations

import socket
from dataclasses import dataclass, field
from typing import Any

from ..utils.logging import get_logger

logger = get_logger(__name__)

OHM_SERVICE_TYPE = "_ohm._tcp.local."


@dataclass
class DiscoveredPeer:
    """A peer found via mDNS browse."""

    name: str
    host: str
    port: int
    did: str | None = None
    properties: dict[str, str] = field(default_factory=dict)


def parse_txt_properties(
    properties: dict[str, bytes | str] | None,
) -> dict[str, str]:
    """Decode zeroconf TXT record properties to strings."""
    if not properties:
        return {}
    out: dict[str, str] = {}
    for key, value in properties.items():
        if isinstance(value, bytes):
            out[key] = value.decode("utf-8", errors="replace")
        else:
            out[key] = str(value)
    return out


def base_url_from_service(peer: DiscoveredPeer) -> str:
    return f"http://{peer.host}:{peer.port}"


class MdnsAdvertiser:
    """Register this node as ``_ohm._tcp`` on the local network."""

    def __init__(self) -> None:
        self._zc: Any | None = None
        self._info: Any | None = None

    def register(
        self,
        *,
        did: str,
        port: int,
        display_name: str,
        host: str | None = None,
    ) -> None:
        from zeroconf import IPVersion, ServiceInfo, Zeroconf

        if self._zc is not None:
            self.unregister()

        bind_host = host or _local_ip_for_mdns()
        self._zc = Zeroconf(ip_version=IPVersion.V4Only)
        properties = {
            "did": did,
            "name": display_name,
            "version": "1",
        }
        self._info = ServiceInfo(
            OHM_SERVICE_TYPE,
            f"{_safe_service_label(display_name)}.{OHM_SERVICE_TYPE}",
            addresses=[socket.inet_aton(bind_host)],
            port=port,
            properties={k: v.encode("utf-8") for k, v in properties.items()},
        )
        self._zc.register_service(self._info)
        logger.info(
            f"mDNS advertised federation peer at {bind_host}:{port} ({OHM_SERVICE_TYPE})"
        )

    def unregister(self) -> None:
        if self._zc and self._info:
            try:
                self._zc.unregister_service(self._info)
            except Exception as e:
                logger.warning(f"mDNS unregister failed: {e}")
        if self._zc:
            self._zc.close()
        self._zc = None
        self._info = None

    def close(self) -> None:
        self.unregister()


class MdnsBrowser:
    """Browse for OHM peers on the LAN (blocking, short timeout)."""

    def browse(self, timeout: float = 3.0) -> list[DiscoveredPeer]:
        from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf

        found: dict[str, DiscoveredPeer] = {}

        class _Listener:
            def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                self._upsert(zc, type_, name)

            def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                self._upsert(zc, type_, name)

            def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                found.pop(name, None)

            def _upsert(self, zc: Zeroconf, type_: str, name: str) -> None:
                info = zc.get_service_info(type_, name)
                if not info:
                    return
                host = socket.inet_ntoa(info.addresses[0]) if info.addresses else ""
                if not host:
                    return
                props = parse_txt_properties(
                    {k: v for k, v in (info.properties or {}).items()}
                )
                found[name] = DiscoveredPeer(
                    name=name,
                    host=host,
                    port=info.port or 8001,
                    did=props.get("did"),
                    properties=props,
                )

        zc = Zeroconf()
        try:
            listener = _Listener()
            browser = ServiceBrowser(zc, OHM_SERVICE_TYPE, listener)
            import time

            time.sleep(timeout)
            browser.cancel()
        finally:
            zc.close()

        return list(found.values())


def browse_mdns_peers(timeout: float = 3.0) -> list[DiscoveredPeer]:
    """Convenience wrapper for LAN peer browse."""
    return MdnsBrowser().browse(timeout=timeout)


def _safe_service_label(display_name: str) -> str:
    label = "".join(c if c.isalnum() else "-" for c in display_name).strip("-")
    return label[:63] or "ohm-node"


def _local_ip_for_mdns() -> str:
    """Pick a non-loopback IPv4 address for service advertisement."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
