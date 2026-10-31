# ADR: `members` visibility level

## Status

Accepted — not yet implemented.

## Date

2026-10-31

## Context

A node can now have **members**: individuals registered on a node they do not
operate. The driving case is a relief organisation (Distribute Aid) that runs a
node, adds its volunteers, and needs to see which of them own a 3D printer so it
can route production requests to them. A member's printer is an OKW facility
authored by that member.

The three existing levels cannot express that. `private` is visible to its
creator only, and `admin` deliberately buys nothing extra in list scope (see
[Identity Model](identity-model.md)), so a coordinator cannot see a volunteer's
private facility. `followers` and `public` are visible to anonymous visitors of
the node *and* enter the federation catalogue, which publishes a volunteer's
home equipment, possibly with its location, to the world and to every
following peer.

## Decision

Add a fourth level, **`members`**: visible to every authenticated account on
this node, and **never** entered in the federation catalogue.

The ladder becomes `private` < `members` < `followers` < `public`.
`is_shareable` (meaning "may leave this node") stays false for `members`, so
catalogue construction and sync are unchanged. Like the other levels it lives
in the visibility plane, outside the manifest and its content hash; legacy
records without a visibility object still resolve to `followers`.

## Considered options

- **Members use `followers`.** No code change, but exposes home equipment to
  anonymous visitors and to peers.
- **A coordinator role that reads members' private records.** Reverses the
  "admin buys nothing extra in list scope" invariant and makes `private` stop
  meaning private — the defect class `tests/parity/test_viewer_scope_ratchet.py`
  exists to prevent.

## Consequences

- `members` is only as private as the node's registration policy. On a node
  with open self-registration it means "anyone who signs up". Nodes that rely
  on it should use invite-only registration.
- A `members` record that appears on a published curated list does not sync;
  list membership never widens visibility.

## Related

- [Identity Model](identity-model.md)
- [Curated lists ADR](curated-lists-adr.md)
