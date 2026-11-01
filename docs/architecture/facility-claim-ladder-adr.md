# ADR: Facility claim / verification ladder (stub)

## Status

Proposed (deferred) — not implemented. Documents the intended ladder so beta
onboarding does not treat local write admin as global ownership.

## Date

2026-07-23

## Context

OHM facility admin (create / edit / delete / Sharing) uses **local write
permission** on this node. Optional soft attribution (`author`) is
self-asserted provenance, not an exclusive claim that a facility “belongs” to
someone across the federation. `on_behalf_of` is no longer self-asserted: it
requires an affiliation (see [Organisation attribution ADR](organisation-attribution-adr.md)),
and even then attributes the record to an organisation rather than claiming
the facility.

Operators and users will still ask “how do I prove this is my fablab?” under
adversarial or multi-operator conditions. Building exclusive claim UX now would
fight the federated model (peers keep their own copies; sync is pull-based;
MoM cards are remote adaptors).

## Decision (deferred product)

**v1 (shipped):** local write admin only. No adversarial exclusive claim UI.

**Future ladder** (document only until a dedicated PRD):

| Rung | Mechanism | Trust gained | Notes |
|---|---|---|---|
| 0 | Soft `author` on create; `on_behalf_of` requires an affiliation | `author` self-asserted; `on_behalf_of` grant-backed | `on_behalf_of` superseded by the [Organisation attribution ADR](organisation-attribution-adr.md) |
| 1 | Domain bind for a space DID | Control of a DNS/web origin | Existing bindings surface |
| 2 | Peer attestations / vouches | Social endorsement | Attestation / reputation APIs exist; scoring deferred |
| 3 | Out-of-band challenge (operator-mediated) | Human verification | Not designed yet |
| — | Global exclusive ownership | — | **Out of scope** — prefer follow-graph + attestations over a single world-writable owner |

Prefer **follow-graph + attestations** over a TOFU “I own this lab worldwide”
button. Synced facilities remain editable locally; edits do not push back to
peers (see federation OKW ingest + UI synced banner).

## Non-goals (this ADR)

- Implementing claim challenges or exclusive locks in product UI
- Treating Maps of Making adaptor rows as locally claimable OKW
- Changing Sharing (visibility / disclosure) semantics

## Consequences

- Docs and UI can link here when users confuse “I can edit this copy” with
  “I own this facility in the network.”
- A future implementation PRD should pick concrete challenge protocols and
  which rungs are automated vs operator-mediated before writing code.

## Related

- [Identity Model](identity-model.md)
- [Federation MVP ADR](federation-mvp-adr.md)
- Product API guide: [`docs-site/docs/guides/use-the-api.md`](../../docs-site/docs/guides/use-the-api.md)
