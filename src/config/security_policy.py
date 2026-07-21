"""Security posture presets for identity, authorization, and trust.

``SecurityMode`` selects a bundle of identity/trust/authz knobs (``SecurityPolicy``).
This is a distinct axis from ``SystemMode`` (matching/validation rigor): a deployment
can combine any matching rigor with any security posture.

All three modes are implemented; consumers read posture from
:func:`get_security_policy` rather than hard-coding it.

See ``docs/architecture/security-modes.md`` and ``notes/federated-identity-adr.md``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
from typing import Any, Dict


class SecurityMode(str, Enum):
    """Deployment security posture."""

    PEACETIME = "peacetime"
    CRISIS = "crisis"
    SHIELDED = "shielded"


@dataclass(frozen=True)
class SecurityPolicy:
    """Identity/trust/authz knobs for a security mode.

    Categorical knobs use documented string values so modes can extend them
    without a schema change.
    """

    mode: SecurityMode
    require_auth_for_writes: bool  # enforce authentication on dataset-mutating requests
    custodial_keys_allowed: bool
    grant_ttl_days: int
    recovery: str  # "reissuance" | "none" (social k-of-n later)
    trust_bootstrap: str  # "tofu_registry" | "tofu_friendly" | "explicit_only"
    mdns_advertise: bool
    metadata_logging: str  # "full" | "minimal"
    registry_attestations: str  # "trust_on_follow" | "ca_pinned"
    # Reserved for Slice M.2 moderated push; shielded disables anonymous submit.
    anonymous_submission_allowed: bool = True

    def to_public_dict(self) -> Dict[str, Any]:
        """JSON-serializable view of the active policy (for API/CLI status)."""
        data = asdict(self)
        data["mode"] = self.mode.value
        return data


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
    anonymous_submission_allowed=True,
)

# Availability under degraded connectivity: long grants, TOFU-friendly, mDNS on.
_CRISIS = SecurityPolicy(
    mode=SecurityMode.CRISIS,
    require_auth_for_writes=True,
    custodial_keys_allowed=True,  # batch onboard
    grant_ttl_days=180,  # long + offline grace
    recovery="reissuance",
    trust_bootstrap="tofu_friendly",
    mdns_advertise=True,
    metadata_logging="full",
    registry_attestations="trust_on_follow",
    anonymous_submission_allowed=True,
)

# Confidentiality under surveillance: short TTLs, no mDNS, minimal metadata.
_SHIELDED = SecurityPolicy(
    mode=SecurityMode.SHIELDED,
    require_auth_for_writes=True,
    custodial_keys_allowed=False,  # discourage node-held person keys
    grant_ttl_days=7,
    recovery="none",
    trust_bootstrap="explicit_only",
    mdns_advertise=False,
    metadata_logging="minimal",
    registry_attestations="ca_pinned",
    anonymous_submission_allowed=False,
)

_PRESETS = {
    SecurityMode.PEACETIME: _PEACETIME,
    SecurityMode.CRISIS: _CRISIS,
    SecurityMode.SHIELDED: _SHIELDED,
}


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
    Crisis and shielded always enforce writes.
    """
    from .settings import ENVIRONMENT

    return ENVIRONMENT == "production"


def get_security_policy(mode: str | SecurityMode | None = None) -> SecurityPolicy:
    """Return the policy for ``mode`` (defaults to the configured ``OHM_SECURITY_MODE``)."""
    if mode is None:
        from .settings import OHM_SECURITY_MODE

        mode = OHM_SECURITY_MODE
    resolved = parse_security_mode(mode)
    policy = _PRESETS[resolved]
    if resolved is SecurityMode.PEACETIME:
        return replace(
            policy,
            require_auth_for_writes=_peacetime_requires_auth_for_writes(),
        )
    return policy


def allows_full_metadata_logging(policy: SecurityPolicy | None = None) -> bool:
    """True when identity/trust events may be logged at INFO with full detail."""
    p = policy if policy is not None else get_security_policy()
    return p.metadata_logging == "full"
