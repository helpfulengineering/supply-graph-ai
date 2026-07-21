# Identity Model

OHM's authorization is **offline-first and federation-ready**. It rests on three
concepts with three different lifetimes. This page documents the pieces that ship
today (self-sovereign identities, capability grants, and record provenance); space
claim and full attestations arrive in later slices.

| Layer | What it is | Lifetime | Bound to |
|---|---|---|---|
| **Identity** | An Ed25519 `did:key` | Permanent (rotatable, never expires) | a person, space, or node |
| **Capability grant** | A signed, forward-looking *permission* | Short-lived, renewable | a subject identity + scope |
| **Attestation** | A signed, backward-looking *fact* | Durable | a subject identity *(future slice)* |

Everything is verifiable **offline**: a grant is checked by verifying an Ed25519
signature against the issuer's DID — no network, no central authority.

## Identities

An identity is a keypair whose public half is encoded as a
[`did:key`](https://w3c-ccg.github.io/did-method-key/) (the same primitive the
federation node uses). Identities are minted for an **account** (person or space)
and are **custodial** at first — the node holds the private key on the owner's
behalf until they claim it.

- Private keys live **node-local**, never in the object store and never federated
  (`OHM_FEDERATION_DATA_DIR/identities/<did>.json`). Plaintext in peacetime;
  encryption-at-rest is on the roadmap.
- **Rotation** mints a fresh keypair and records a signed `IdentityLink`
  (`from_did → to_did`, signed by the *old* key) so reputation follows the chain
  rather than a single key.

```bash
ohm identity identities create --account-id <uuid> --kind person --name "Ada"
ohm identity identities show did:key:z...
ohm identity identities rotate did:key:z...
```

## Capability grants

A grant is a signed statement: *"issuer_did says subject_did may do
&lt;permissions&gt; on &lt;scope&gt; until expires_at."*

- **Scope** is versioned — `{kind, target, v}` — where `kind` is one of
  `node` / `space` / `pool` / `record`. An **unknown scope kind denies all**
  (fail closed).
- **Permissions** reuse the base vocabulary (`read` / `write` / `admin` /
  `domain:x`) plus richer verbs (`publish` / `certify` / `moderate` / `own`).
  Verbs a node does not understand are dropped at resolution.
- **`coarse_floor`** is a subset of the base vocabulary that is honored even by a
  node unaware of the richer verbs — the guaranteed minimum.
- **Expiry, not revocation lists.** Grants are short-lived and renewed by
  re-contacting the issuer, so an offline network "revokes" simply by letting a
  grant lapse.

```bash
ohm identity grants issue --subject-did did:key:z... \
    --permission write --scope-kind node --scope-target did:key:z<node> --ttl-days 90
ohm identity grants list --subject-did did:key:z...
ohm identity grants revoke <grant_id>
```

### How a grant is honored (resolution)

`resolve_capabilities(subject_did, scope)` unions the effective permissions of
every matching grant that passes all of:

1. **Signature** verifies against `issuer_did`'s public key.
2. **Time window** — `not_before ≤ now < expires_at`.
3. **Scope kind is known** — otherwise the grant contributes nothing.
4. **Scope matches** the requested scope (`kind` + `target` + `v`).
5. **Issuer is trusted** — for now, the local node identity, or a *self-asserted*
   issuer (`issuer == subject`, the isolated-edge bootstrap case, honored locally
   but carrying no global weight until a peer endorses it).
6. Effective permissions = known verbs from `permissions` ∪ `coarse_floor`.

## Record provenance

Where identities and grants answer *"who may write?"*, **provenance** answers
*"who made this record?"* — the authorship/publication facts attached to an OKH
manifest or OKW facility.

- **`Credit`** attributes one contributor by either a `subject_did` *or* a
  claimable `external_id` (e.g. `orcid:0000-…`, `name:Jane Doe`) — exactly one of
  the two. An unclaimed external credit can be bound to a real DID later.
- A record's provenance carries `authored_by[]`, `published_by` (a DID), and
  `on_behalf_of` (a space DID), and may be **signed** by the author/space key for
  offline authorship verification (`sign_provenance` / `verify_provenance` reuse
  the same `did:key` crypto).
- Provenance lives in its **own store** keyed by record id, deliberately *outside*
  the manifest, so it never enters the design **content hash** — the same design
  published by two people still deduplicates.

On create, the API stamps provenance from the authenticated subject; `--author`
and `--on-behalf-of` override the defaults. Read it back per record:

```bash
# create attributes to the caller by default; override with flags
curl -X POST "$OHM/api/okh/create?on_behalf_of=did:key:z<space>" -d @manifest.json

ohm okh provenance <manifest_id>
ohm okw provenance <facility_id>
```

**Across federation**, provenance rides the **node-signed catalog record** (not
the manifest, so it never enters the content hash). On ingest a peer verifies the
author's signature when the claim is signed — a *signed-but-invalid* claim is
rejected, an unsigned claim is relayed as an unverified assertion — then re-stamps
it into its own provenance plane. So a design authored by user U at node A shows U
as author after syncing to node B.

## Relationship to API keys

API keys are unchanged and still work: a key's permission list acts as an
**implicit grant** for its account. When a key's account has a primary DID and a
request is authorized against a scope, capability grants for that DID are
**unioned** with the key's own permissions — grants can only *add* capability, so
existing clients keep working exactly as before. See [Authentication](../api/auth.md).

## Trust roots today, and where this is going

Single-node peacetime uses the **local node identity** as the trust root, with
self-asserted edge bootstrap allowed locally. As federation grows, trust roots
extend to followed peers (peer-as-issuer for its edge cluster) and the identity
chain becomes the substrate for provenance and reputation. See
`notes/federated-identity-adr.md` for the full roadmap.
