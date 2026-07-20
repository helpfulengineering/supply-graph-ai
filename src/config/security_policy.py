"""Security posture presets for identity, authorization, and trust.

``SecurityMode`` selects a bundle of identity/trust/authz knobs (``SecurityPolicy``).
This is a distinct axis from ``SystemMode`` (matching/validation rigor): a deployment
can combine any matching rigor with any security posture.

Only ``PEACETIME`` is implemented; ``CRISIS`` and ``SHIELDED`` are reserved so their
policies can be slotted in later without changing call sites — every consumer reads
its posture from :func:`get_security_policy` rather than hard-coding it.

See ``docs/architecture/security-modes.md`` and ``notes/federated-identity-adr.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class SecurityMode(str, Enum):
    """Deployment security posture. Peacetime implemented; others reserved."""

    PEACETIME = "peacetime"
    CRISIS = "crisis"
    SHIELDED = "shielded"


@dataclass(frozen=True)
class SecurityPolicy:
    """Identity/trust/authz knobs for a security mode.

    Categorical knobs use documented string values so future modes can extend them
    without a schema change; unknown values are the reserved modes' concern.
    """

    mode: SecurityMode
    require_auth_for_writes: bool  # enforce authentication on dataset-mutating requests
    custodial_keys_allowed: bool
    grant_ttl_days: int
    recovery: str  # "reissuance" (peacetime); future: "social" | "none"
    trust_bootstrap: str  # "tofu_registry"; future: "explicit_only"
    mdns_advertise: bool
    metadata_logging: str  # "full"; future: "minimal"
    registry_attestations: str  # "trust_on_follow"; future: "ca_pinned"


_PEACETIME = SecurityPolicy(
    mode=SecurityMode.PEACETIME,
    # Placeholder; get_security_policy() resolves this per-environment (see below).
    require_auth_for_writes=True,
    custodial_keys_allowed=True,
    grant_ttl_days=90,
    recovery="reissuance",
    trust_bootstrap="tofu_registry",
    mdns_advertise=True,
    metadata_logging="full",
    registry_attestations="trust_on_follow",
)


def parse_security_mode(value: str | SecurityMode | None) -> SecurityMode:
    """Parse a mode from a config string (mirrors ``parse_node_role``)."""
    if isinstance(value, SecurityMode):
        return value
    normalized = (value or "peacetime").strip().lower()
    try:
        return SecurityMode(normalized)
    except ValueError as exc:
        valid = ", ".join(m.value for m in SecurityMode)
        raise ValueError(
            f"Invalid OHM_SECURITY_MODE {value!r}; expected {valid}"
        ) from exc


def _peacetime_requires_auth_for_writes() -> bool:
    """Peacetime posture: enforce write auth in production, relax in dev/test.

    This preserves existing unauthenticated dev/test flows while closing the write
    hole for real deployments. Override by running with ``ENVIRONMENT=production``.
    """
    from .settings import ENVIRONMENT

    return ENVIRONMENT == "production"


def get_security_policy(mode: str | SecurityMode | None = None) -> SecurityPolicy:
    """Return the policy for ``mode`` (defaults to the configured ``OHM_SECURITY_MODE``)."""
    if mode is None:
        from .settings import OHM_SECURITY_MODE

        mode = OHM_SECURITY_MODE
    resolved = parse_security_mode(mode)
    if resolved is SecurityMode.PEACETIME:
        return replace(
            _PEACETIME,
            require_auth_for_writes=_peacetime_requires_auth_for_writes(),
        )
    raise NotImplementedError(
        f"SecurityMode {resolved.value!r} is reserved; only 'peacetime' is implemented."
    )
