# Security Modes

OHM's **Security Mode** selects the deployment's identity, authorization, and trust
posture. It is a **distinct axis** from `SystemMode` (which governs matching/validation
rigor: `minimal` / `standard` / `strict`). The two are independent — any matching rigor
can combine with any security posture.

Configure it with a single environment variable:

```bash
OHM_SECURITY_MODE=peacetime   # or crisis | shielded
```

At runtime, code reads its posture from a `SecurityPolicy` rather than hard-coding
behavior:

```python
from src.config import get_security_policy

policy = get_security_policy()          # uses OHM_SECURITY_MODE
policy = get_security_policy("shielded")  # or an explicit mode
```

```bash
ohm identity security-policy
```

## Modes

| Mode | Optimizes for |
|------|---------------|
| `peacetime` | Convenience — normal, non-adversarial operation |
| `crisis` | Availability under degraded connectivity |
| `shielded` | Confidentiality / deniability under surveillance |

Security Mode is a **threat posture, not an urgency level**: a non-adversarial emergency
response runs `peacetime`. `crisis` and `shielded` address adversarial or surveilled
networks.

## Policy knobs by mode

| Knob | Peacetime | Crisis | Shielded |
|------|-----------|--------|----------|
| `require_auth_for_writes` | prod only | always | always |
| `custodial_keys_allowed` | yes | yes (batch onboard) | **no** |
| `grant_ttl_days` | 90 | 180 | 7 |
| `recovery` | `reissuance` | `reissuance` | `none` |
| `trust_bootstrap` | `tofu_registry` | `tofu_friendly` | `explicit_only` |
| `mdns_advertise` | on | on | **off** |
| `metadata_logging` | `full` | `full` | `minimal` |
| `registry_attestations` | `trust_on_follow` | `trust_on_follow` | `ca_pinned` |
| `anonymous_submission_allowed` | yes | yes | **no** (Slice M.2) |

## What is wired today

- **Grant TTL** — `issue_grant` defaults to `grant_ttl_days`.
- **Write auth** — `require_write` / `require_admin` honor `require_auth_for_writes`.
- **Custodial mint** — `create_identity` is refused when `custodial_keys_allowed` is false.
- **mDNS** — advertise and browse require env flag **and** role capability **and**
  `mdns_advertise` (so shielded never LAN-announces).
- **Directory** — under `ca_pinned`, `list_directory` only returns entries with a verified
  domain binding.
- **Metadata logging** — under `minimal`, identity-mint info logs drop DID/account detail.
- **`anonymous_submission_allowed`** — reserved for moderated upstream push (Slice M.2).

See `notes/federated-identity-adr.md` for the design rationale.
