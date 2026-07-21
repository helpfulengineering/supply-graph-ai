# Identity Model

!!! tip "Operator how-to"
    For bootstrap, accounts, keys, and the Settings UI, see
    **[Authentication & IAM](../auth/index.md)**. This page documents the trust
    model and the pieces that ship today (identities, grants, provenance,
    visibility, space claims, and attestations).

OHM's authorization is **offline-first and federation-ready**. It rests on three
concepts with three different lifetimes. This page documents the pieces that ship
today (identities, grants, provenance, visibility, space claims, and attestations).

| Layer | What it is | Lifetime | Bound to |
|---|---|---|---|
| **Identity** | An Ed25519 `did:key` | Permanent (rotatable, never expires) | a person, space, or node |
| **Capability grant** | A signed, forward-looking *permission* | Short-lived, renewable | a subject identity + scope |
| **Attestation** | A signed, backward-looking *fact* | Durable | a subject identity (+ optional content hash) |

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
ohm okh create my-design.okh.json --author did:key:z… --on-behalf-of did:key:z…
ohm okw create my-lab.okw.json --author orcid:0000-0001-…

ohm okh provenance <manifest_id>
ohm okw provenance <facility_id>
```

**Across federation**, provenance rides the **node-signed catalog record** (not
the manifest, so it never enters the content hash). On ingest a peer verifies the
author's signature when the claim is signed — a *signed-but-invalid* claim is
rejected, an unsigned claim is relayed as an unverified assertion — then re-stamps
it into its own provenance plane. So a design authored by user U at node A shows U
as author after syncing to node B.

## Record visibility (share policy)

Where provenance answers *"who made this?"*, **visibility** answers *"how far may
it leave this node?"* — local publishing policy, also in its own store (out of the
content hash). It is **not** federated: a receiving node decides what to re-share.

| Level | In federation catalog? |
|---|---|
| `private` | No (create default) |
| `followers` | Yes (peers that sync from this node) |
| `public` | Yes (same catalog filter today; reserved for registry listing later) |

Pre-Slice-4 records with no visibility object are treated as `followers` so existing
catalogs do not empty. New creates stamp `private` — promote explicitly to share:

```bash
ohm okh visibility set <manifest_id> public
ohm okh visibility show <manifest_id>
ohm okw visibility set <facility_id> followers
```

## Relationship to API keys

API keys are unchanged and still work: a key's permission list acts as an
**implicit grant** for its account. When a key's account has a primary DID and a
request is authorized against a scope, capability grants for that DID are
**unioned** with the key's own permissions — grants can only *add* capability, so
existing clients keep working exactly as before. See [Authentication](../api/auth.md).

## Spaces (admin claim)

A **space** is an identity (`kind=space`) that persons administer and publish on
behalf of. Claiming is **TOFU**: the first admin bind wins; the space key signs
the claim so it is offline-verifiable. Optional domain binding is available (see
below) and is additive — informal spaces without a domain still work.

```bash
ohm identity identities create --account-id <uuid> --kind space --name "MIT FabLab"
ohm identity spaces claim --space-did did:key:z… --admin-did did:key:z…
ohm identity spaces show did:key:z…
```

A claimed space admin may issue **space-scoped** grants
(`scope.kind=space`, `scope.target=<space_did>`); those are honored at resolution.

## Attestations (certification / reputation)

An **attestation** is a signed, durable fact: *"issuer_did asserts `<type>` about
subject_did (optionally over content_hash)."* Unlike grants, attestations do not
expire by default and do not confer permission — they are reputation inputs.

- **`type`** is an open string with well-known constants (`authored`, `published`,
  `certified`, `vouch`, `space_member`, …). Unknown types are stored and federated
  but ignored by reputation helpers until understood.
- **R3 certification** binds firm DID → **bundle hash** → version. The bundle hash
  is a Merkle root over `{manifest_content_hash + sorted per-file checksums}` from
  a package pin record (`packaging.pin.bundle_hash`).
- Attestations live in their **own store** (out of the design content hash) and
  **ride the node-signed catalog record**. On ingest, peers verify each attestation
  signature (fail closed) and re-stamp into the local plane.

```bash
ohm identity attestations certify \
    --subject-did did:key:zFirm \
    --bundle-hash sha256:… \
    --version 1.2.0 \
    --manifest-content-hash sha256:…
ohm identity attestations list --subject-did did:key:zFirm
ohm identity reputation did:key:zFirm
```

`reputation` returns known-type, signature-valid attestations about a subject —
no numeric scoring yet.

## Optional bindings (domain / OAuth)

Bindings are an **online convenience layer** on top of `did:key`. They are never
required for offline authz. A verified binding is durable evidence (and issues a
`domain_bound` / `oauth_bound` attestation).

**Domain** — prove control of a host by publishing
`https://{domain}/.well-known/ohm-did.json` with the DID + a one-time challenge:

```bash
ohm identity bindings domain-start --subject-did did:key:z… --domain example.org
# host the printed JSON at /.well-known/ohm-did.json, then:
ohm identity bindings domain-verify --subject-did did:key:z… --domain example.org
```

**OAuth / OIDC** — the IdP redirect dance lives in the frontend; once claims are
accepted, record the binding:

```bash
ohm identity bindings oauth --subject-did did:key:z… \
    --provider github --external-subject ada-lovelace
ohm identity bindings list --subject-did did:key:z…
```

## Trust-on-follow directory

Peacetime registry posture is a **local directory** of known DIDs (with optional
verified bindings and base URLs) that operators use when deciding who to follow —
not a central CA. Verified domain/OAuth binds refresh the subject's directory row
automatically.

```bash
ohm identity directory publish --did did:key:z… --name "MIT FabLab" \
    --base-url http://fablab.example:8001
ohm identity directory list
```

## Trust roots today, and where this is going

Grant issuers this node trusts:

1. **Local node identity** — always.
2. **Self-asserted** (`issuer == subject`) — isolated edge genesis; local only.
3. **Claimed space admin** — for grants scoped to that space.
4. **Followed peer DID** — peer-as-issuer for its cluster.

```bash
# Isolated edge: self-issue write on the local node
ohm identity grants bootstrap-edge --subject-did did:key:z…
```

See `notes/federated-identity-adr.md` for the full roadmap.
