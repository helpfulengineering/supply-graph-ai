# Authentication & IAM

OHM’s peacetime access model is **API-key first**, with optional **self-sovereign
identities** (`did:key`) and **capability grants** for offline-verifiable
authorization. This section is the operator-facing guide: how to bootstrap a
node, create accounts and keys, mint identities, and use the Settings UI.

## Concepts at a glance

| Concept | What it is | Typical lifetime |
|---|---|---|
| **API key** | Bearer token for HTTP/CLI session (`Authorization: Bearer …`) | Until revoked or rotated |
| **Account** | Custodial unit (person or space) that owns keys and that DIDs bind to | Long-lived |
| **Identity (DID)** | Ed25519 `did:key` keypair; custodial on the node until claimed | Permanent (rotatable) |
| **Capability grant** | Signed, time-bounded permission on a scope | Short-lived, renewable |
| **Security mode** | Node posture (`peacetime` / `crisis` / `shielded`) | Deployment config |

These layers are **additive**. An API key’s flat permissions (`read` / `write` /
`admin`) are the session floor. Grants can *add* capability for a DID-backed
subject; they never remove the key’s floor.

!!! tip "Order of operations"
    1. Bootstrap with `API_KEYS` (env / Container App secret).
    2. Connect in the UI (or set `OHM_API_KEY` for the CLI).
    3. Create an **account** under Keys & accounts.
    4. Optionally mint a **DID** for that account under Identities.
    5. Issue **grants** and day-to-day **storage keys** as needed.

## Guides in this section

| Page | Audience |
|---|---|
| [Getting Started](getting-started.md) | First deploy: env keys, Azure, Connect |
| [Accounts & API Keys](accounts-and-keys.md) | Creating accounts, storage keys, permissions |
| [Identities & Grants](identities-and-grants.md) | Minting DIDs, rotation, capability grants |
| [Frontend Settings](frontend.md) | Browser UI walkthrough |

## Related architecture docs

- [Identity Model](../architecture/identity-model.md) — trust, grants, provenance, visibility, attestations
- [Security Modes](../architecture/security-modes.md) — peacetime / crisis / shielded policy knobs
- [API Authentication](../api/auth.md) — header format, endpoint dependencies, developer reference
