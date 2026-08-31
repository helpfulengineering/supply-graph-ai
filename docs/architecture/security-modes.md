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
| `open_registration` | yes | yes | **no** |
| `key_ttl_days` | 180 | 365 (offline grace) | 30 |
| `admin_break_glass` | **no** | yes (recorded) | **no** |

## Who may speak for the client

Everything keyed on a caller's address — the rate limiter, request logs, metrics
— is only as trustworthy as the set of proxies allowed to rewrite it.

Uvicorn's proxy-headers middleware replaces `request.client` with the address in
`X-Forwarded-For` **when the immediate peer is trusted**, and ignores the header
entirely when it is not. `FORWARDED_ALLOW_IPS` names those peers.

| Value | Effect |
|---|---|
| default (loopback + RFC1918) | Platform ingress is believed; a direct public caller's forwarded headers are ignored |
| `*` | **Every** peer is believed, and uvicorn then takes the *leftmost* `X-Forwarded-For` entry — the part the caller writes |

It was `*`. That is why the per-client rate limit could be evaded by sending a
different forwarded address on each request, and why one caller could exhaust
another's budget by naming them. The setting exists for a real reason —
`X-Forwarded-Proto` must be trusted or Starlette builds `http://` redirects
behind a TLS-terminating ingress — so the fix was to name the proxies, not to
stop trusting them. See `src/config/proxy_trust.py`.

**If your topology differs** — a reverse proxy on a public address, a service
mesh, an ingress outside the private ranges — set `FORWARDED_ALLOW_IPS` to that
proxy's address or CIDR. Widening it back to `*` is supported but means any peer
can claim to be any client.

**The limiter counts per process.** With N workers the effective budget is
N x the configured rate: loose but bounded, and adequate for a coarse abuse
brake. It is not adequate for anything that must count exactly — an attempt
limit on a guessable secret needs shared state, because N chances per window
instead of one is the difference between a limit and a suggestion.

## What is wired today

- **Grant TTL** — `issue_grant` defaults to `grant_ttl_days`.
- **Write auth** — `require_write` / `require_admin` honor `require_auth_for_writes`.
- **Custodial mint** — `create_identity` is refused when `custodial_keys_allowed` is false.
- **Self-service registration** — `POST /api/identity/register` is refused when
  `open_registration` is false; shielded onboards out of band instead.
- **mDNS** — advertise and browse require env flag **and** role capability **and**
  `mdns_advertise` (so shielded never LAN-announces).
- **Directory** — under `ca_pinned`, `list_directory` only returns entries with a verified
  domain binding.
- **Metadata logging** — under `minimal`, identity-mint info logs drop DID/account detail.
- **`anonymous_submission_allowed`** — reserved for moderated upstream push (Slice M.2).

See `notes/federated-identity-adr.md` for the design rationale.
