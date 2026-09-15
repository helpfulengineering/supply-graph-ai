# ADR: Asset visibility is ownership, and nothing else

## Status

Accepted (2026-09-14). Implemented for #493.

## Context

`AssetRecord` is the third top-level domain object — design (OKH), capability
(OKW), **physical state** (asset). It is the one most likely to describe a real
place and the people at it: an asset carries `asset_tag`, `location`,
`triage_notes`, and per component `condition`, `notes`, `assessed_by`,
`claimed_by`.

Every asset read was anonymous and unscoped. `AssetService.list()` took no
viewer, the service had no visibility plane, and
`GET /v1/api/asset` served every asset on the node to any caller. #492 closed
the writes on this surface; the reads were never the part anyone chose to make
public.

Assets do **not** ride the federation catalogue, so the exposure was to anyone
who could reach the node, not to peers, and it did not widen when federation was
enabled.

## Decisions

**1. The owner is the creating account.** The same `ohm_created_by` mechanism
OKH and OKW use, so there is one `ViewerScope`, one notion of "the caller's own",
and one ratchet watching all three surfaces.

Not the facility: [the facility claim ladder](facility-claim-ladder-adr.md)
explicitly defers facility ownership — v1 is local write admin only, and global
exclusive ownership is out of scope. Hanging asset access off it would import an
unsettled ownership model into an access-control decision.

**Space-DID ownership is the intended end state**, not the starting point.
`Scope(kind="space")` already exists and is already honoured by
`resolve_capabilities`, so a facility admin could later grant asset access to
their technicians with no new authorization code — grants only ever *add*, so
that upgrade is additive. Starting there would make the common case (one person,
one node, some assets) require minting and claiming a space before anything was
visible.

**2. There is no visibility level, and therefore no way to share an asset.**
Owner scoping alone closes the exposure, because an anonymous caller owns
nothing. A visibility plane would mean get/set endpoints, and by this project's
definition of done that means API, CLI, docs and parity rows — real surface for a
capability nothing is asking for.

The filter still calls `visible_to(None, viewer, did, account)` rather than
`viewer.owns(...)` directly, so that adding a level later needs no change at the
call site.

**If sharing is ever wanted, adopt `VisibilityStore` and `VisibilityLevel`
unchanged** rather than inventing an asset-specific vocabulary. The store is
keyed by bare record id with no type component, so reuse costs no new storage
code. One thing to resolve first: `public` on an OKH means "anyone, including
through the federation catalogue", while `public` on an asset would mean "anyone
who can reach this node". Same word, two blast radii.

**3. An asset with no owner is readable by nobody.** No legacy rule, no
fallback. OKH and OKW fail *open* for records predating their visibility plane —
absence resolves to `followers` — so that existing catalogues did not empty. The
asset equivalent would re-create the defect permanently for every record written
before the fix, so assets fail closed instead.

The unscoped path (`viewer=None`) remains for trusted internal callers — the CLI
— which is the escape hatch if a node ever does hold unowned assets.

**4. `salvage-match` searches only the caller's own fleet.** Its job is "do I
have a spare pump anywhere in my own fleet", which owner scoping delivers with no
new concept.

Searching *across owners* is a different feature: it needs consent to publish
component-level availability, a contact route, and a trust story about who
asserts the part exists. That is the machinery the federation share list is
being built for. A redacted salvage projection — component, condition, harvest
viability, without `location` or `triage_notes` — mirroring how OKW already
serves redacted facility projections to peers, is the shape worth wanting.

## Consequences

- `AssetService.list()` and `.get()` take a `viewer`; every request handler
  passes one, and `asset_service` is in `SCOPED_SERVICES` so a future unscoped
  list fails the build.
- Attribution is read off the **raw stored dict**, because `to_dict()` is a
  whitelist that drops `ohm_*` keys.
- Writes remain node-wide: any caller with write permission can update an asset
  whose id they know, as for OKH and OKW. Per-record *write* ownership is a
  separate question and is not decided here.
- The CLI cannot authenticate to a remote node, so `ohm asset list` against a
  server returns the anonymous view. Its in-process fallback is unscoped, which
  is the supported path for an operator on the node itself.

## Related

- [Identity model](identity-model.md)
- [Route authorization](route-authorization.md)
- [Facility claim ladder](facility-claim-ladder-adr.md)
