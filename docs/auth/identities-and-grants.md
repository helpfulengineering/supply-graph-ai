# Identities & Grants

Beyond API keys, OHM supports **self-sovereign identities** and **capability
grants**. This page is the operator how-to. For trust and resolution rules, see
the [Identity Model](../architecture/identity-model.md).

## Identities (`did:key`)

An identity is an Ed25519 keypair whose public half is encoded as a
[`did:key`](https://w3c-ccg.github.io/did-method-key/). Identities are minted for
an **existing account** and are **custodial** at first — the node holds the
private key until the owner claims it.

!!! important "Account required first"
    Minting binds a DID to an `account_id`. If Settings → Identities shows an
    empty **Account** dropdown, create an account under
    [Keys & accounts](accounts-and-keys.md) first. Connecting with an env
    `API_KEYS` token does **not** populate that list by itself.

Private keys stay **node-local** (never in the object store, never federated).
Rotation mints a new keypair and records a signed link from the old DID to the
new one so reputation can follow the chain.

### Mint

**UI:** Settings → **Identities** → select account → kind → display name → Mint.

**CLI:**

```bash
ohm identity identities create --account-id <uuid> --kind person --name "Ada"
ohm identity identities show did:key:z...
ohm identity identities rotate did:key:z...
```

**API:** `POST /v1/api/identity/identities` with `account_id`, `kind`, and
`display_name`.

Custodial minting can be disabled by security policy (`custodial_keys_allowed`).
In **shielded** mode the UI and API refuse mint CTAs accordingly.

### Look up and rotate

Use **Look up DID** in the Identities panel (or `ohm identity identities show`)
to load a DID into the session-local list. **Rotate** confirms and replaces the
key; the DID string changes.

## Capability grants

A grant is a signed statement: *issuer says subject may do `<permissions>` on
`<scope>` until `expires_at`.*

- Scopes use `{kind, target, v}` with kinds such as `node` / `space` / `pool` /
  `record` (unknown kinds deny closed).
- Permissions reuse `read` / `write` / `admin` / `domain:x` plus richer verbs
  (`publish` / `certify` / `moderate` / `own`).
- Grants are short-lived; “revocation” offline is mainly letting them expire.

**UI:** Settings → **Grants** (issue / list / revoke; edge bootstrap where
exposed).

**CLI:**

```bash
ohm identity grants issue --subject-did did:key:z... \
  --permission write --scope-kind node --scope-target did:key:z<node> --ttl-days 90
ohm identity grants list --subject-did did:key:z...
ohm identity grants revoke <grant_id>
```

A key’s flat permissions act as an implicit floor: grants can only **add**
capability for a DID-backed subject, never remove the key’s permissions.

### Edge bootstrap

Isolated-edge setups can self-issue a genesis write grant on the local node
scope (`ohm identity grants bootstrap-edge` /
`POST /v1/api/identity/grants/bootstrap-edge`). See the Identity Model for trust
limits of self-asserted issuers.

## Spaces, bindings, directory, federation

Related admin surfaces (also under Settings when you have `admin`):

| Surface | Purpose |
|---|---|
| **Spaces** | Claim a space DID (TOFU — first claim wins) |
| **Bindings** | Domain / OAuth binding records |
| **Directory** | Trust-on-follow directory publish / list |
| **Federation** | Peers, follow/unfollow, sync (requires federation enabled) |

Deep design notes: [Identity Model](../architecture/identity-model.md),
[Federation MVP ADR](../architecture/federation-mvp-adr.md),
[Security Modes](../architecture/security-modes.md).

## See also

- [Accounts & API Keys](accounts-and-keys.md)
- [Frontend Settings](frontend.md)
- [Identity Model](../architecture/identity-model.md)
