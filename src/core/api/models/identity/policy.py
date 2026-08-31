"""Public security-policy response model (#373).

Derived from ``tests/api/golden/identity_security_policy.json``.

**Keep this in step with :class:`~src.config.security_policy.SecurityPolicy`.**
The route returns ``to_public_dict()``, an ``asdict`` of that dataclass, so a
knob added there and not here would be silently filtered out of the response —
the exact failure a response model introduces. The golden in
``tests/integration/test_okh_misc_contract.py`` fails when the two diverge,
which is what makes this a coupling with a gate rather than a comment.
"""

from pydantic import BaseModel


class SecurityPolicyResponse(BaseModel):
    """The deployment's identity/trust posture. Knobs, not secrets."""

    mode: str
    require_auth_for_writes: bool
    custodial_keys_allowed: bool
    grant_ttl_days: int
    recovery: str
    trust_bootstrap: str
    mdns_advertise: bool
    metadata_logging: str
    registry_attestations: str
    anonymous_submission_allowed: bool
    open_registration: bool
    key_ttl_days: int
    admin_break_glass: bool
