# ADR: Organisation attribution (`on_behalf_of`)

## Status

Accepted. Create refuses an `on_behalf_of` that is not a current affiliation,
the publisher signs, and the evidence chain is stored (#577). The
organisation's admin affiliates, renews, and unaffiliates from the UI and
CLI, and a sole affiliation is the default on new records (#578). Verification on
receipt is #588. Adding attribution to an existing record is #589. Supersedes
rung 0 of the [Facility claim ladder](facility-claim-ladder-adr.md) for
`on_behalf_of`.

## Date

2026-10-31

## Context

Record provenance carries `on_behalf_of`: the organisation (a space identity) a
record is published for. It has been self-asserted — free text, accepted from
any caller, never checked. Worse, when the node holds the organisation's key it
signs the claim *as the organisation* for whoever asked. A stranger can publish
"on behalf of Distribute Aid" with a valid signature, and a receiving node
cannot tell.

Volunteer organisations want to track the provenance of their members' designs,
across nodes. That only works if the attribution means something wherever it is
read.

The identity model already separates the two mechanisms involved: **grants**
confer permission and expire; **attestations** are durable reputation facts and
"do not confer permission" ([Identity Model](identity-model.md)). A claimed
space admin can issue a space-scoped `publish` grant, and that trust root is
implemented and tested — it was just never consulted on create.

## Decision

1. **Authority is a grant.** An **affiliation** is a space-scoped `publish`
   grant issued by the organisation's claimed admin. Revoking it un-affiliates;
   it expires with the security mode's grant lifetime and is renewed by the
   admin. No attestation is involved.
2. **Refuse at create.** `on_behalf_of` is accepted only when the caller holds a
   current affiliation to that organisation. Callers with no DID (environment
   API keys, dev-local) are refused. Free text and unclaimed DIDs fail the same
   check.
3. **The publisher signs, never the organisation.** The node no longer signs
   provenance with an organisation's key on a caller's behalf.
4. **Carry the evidence.** Provenance stores the chain that authorised it — the
   organisation's space claim (signed by the space key, naming its admin), the
   admin's grant to the member, and the member's signature — in the provenance
   plane, outside the content hash. Every link is offline-verifiable.
5. **Verified or unverified, never dropped.** A receiving node (federation
   ingest, collection import) verifies the chain. If it holds, the organisation
   is shown as verified; if it is missing or fails, the record is kept and the
   organisation is shown as an unverified claim. *Unverified* means "this node
   could not check" — a remote, legacy or older-peer record — never "checked and
   refused".
6. **Attribute later.** A record's owner may add or remove `on_behalf_of` after
   creation once affiliated, under the same check, captured when added. A
   refusal at create is "not yet", not "never".

A lapsed affiliation stops new records naming the organisation; records signed
while it was held keep their provenance.

## Considered options

- **Gate on a `space_member` attestation.** Contradicts the identity model's
  split, makes attestations a permission source everywhere, and attestations
  have no revoke path.
- **Accept unaffiliated claims, labelled unverified.** Keeps the spoof with a
  label most readers will not notice, and still leaves a legitimate
  not-yet-affiliated member's records unverified forever.
- **Trust the publishing node.** Leaves attribution forgeable by any node
  operator.
- **Let the operator's environment admin key bypass the check.** Reopens the hole
  for anyone holding that key, and produces records whose chain cannot verify on
  peers.

## Consequences

- Behaviour change: API and CLI callers passing an arbitrary `on_behalf_of` are
  refused. The web form becomes a picker of the caller's own affiliations in the
  same change, so the UI never presents a field it will refuse.
- Existing records keep their stored `on_behalf_of` and display as unverified.

## Related

- [Identity Model](identity-model.md)
- [Facility claim ladder](facility-claim-ladder-adr.md)
- [Curated lists ADR](curated-lists-adr.md)
