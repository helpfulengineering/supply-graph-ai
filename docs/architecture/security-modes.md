# Security Modes

OHM's **Security Mode** selects the deployment's identity, authorization, and trust
posture. It is a **distinct axis** from `SystemMode` (which governs matching/validation
rigor: `minimal` / `standard` / `strict`). The two are independent — any matching rigor
can combine with any security posture.

Configure it with a single environment variable:

```bash
OHM_SECURITY_MODE=peacetime   # crisis | shielded are reserved
```

At runtime, code reads its posture from a `SecurityPolicy` rather than hard-coding
behavior, so additional modes slot in without touching call sites:

```python
from src.config import get_security_policy

policy = get_security_policy()          # uses OHM_SECURITY_MODE
policy = get_security_policy("peacetime")  # or an explicit mode
```

## Modes

| Mode | Status | Optimizes for |
|------|--------|---------------|
| `peacetime` | **Implemented** | Convenience — normal, non-adversarial operation |
| `crisis` | Reserved | Availability under degraded connectivity |
| `shielded` | Reserved | Confidentiality / deniability under surveillance |

Security Mode is a **threat posture, not an urgency level**: a non-adversarial emergency
response runs `peacetime`. `crisis` and `shielded` address adversarial or surveilled
networks and currently raise `NotImplementedError`.

## Peacetime policy

| Knob | Value |
|------|-------|
| `custodial_keys_allowed` | `true` |
| `grant_ttl_days` | `90` |
| `recovery` | `reissuance` |
| `trust_bootstrap` | `tofu_registry` |
| `mdns_advertise` | `true` |
| `metadata_logging` | `full` |
| `registry_attestations` | `trust_on_follow` |

See `notes/federated-identity-adr.md` for the design rationale behind these knobs and
the reserved modes.
