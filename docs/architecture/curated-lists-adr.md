# ADR: Curated lists as selective follow

## Status

Accepted — not yet implemented.

## Date

2026-10-31

## Context

Federation sync is all-or-nothing per peer: following a node's DID pulls every
shareable record it publishes (see [Federation MVP ADR](federation-mvp-adr.md)).
Node admins want to sync *some* designs across nodes, and organisations want to
publish vetted sets — "Distribute Aid: field-validated designs" — that other
nodes can track. The existing collection zip is offline and one-shot; it cannot
deliver a later revision.

## Decision

A **curated list** is a named, signed set of **pinned content hashes**,
published by a node or an organisation. A node **subscribes** to a list; a
subscription is a follow scoped to that list, and sync pulls exactly the listed
designs, including later additions. Following a whole node remains the
"everything" case.

- **Entries are pinned versions, not designs.** An author's later edit does not
  change the list; the publisher bumps the entry deliberately. The signature
  covers specific bytes, so a subscriber can verify it holds what was vouched
  for.
- **Keep and mark.** When an entry is bumped or removed, subscribers pull the
  new version and keep the old one, labelled "superseded on list X" or "removed
  from list X". Nothing is deleted on a subscriber because of a remote change.
- **Lists never widen visibility.** A `private` or `members` design on a
  published list does not sync.

## Considered options

- **Entries track the latest version of a design.** Lets untested edits flow
  into a "validated" list, and needs a cross-node design lineage identifier that
  does not exist — sync is keyed by content hash alone.
- **Mirror the list exactly (delete on removal).** Tidier, but grants remote
  nodes a delete capability over local data that this federation model never
  grants; a node that built 200 units from a superseded version must still find
  it.
- **Curated list as a browsable page with "import these".** Cheaper, but
  revisions never reach the people who imported.

## Consequences

- Closes the core of #134 (selective replication) without a general filter
  language.
- Collection zips stay for offline transfer and must carry provenance, so
  affiliation survives the trip.

## Related

- [Federation MVP ADR](federation-mvp-adr.md)
- [`members` visibility ADR](members-visibility-adr.md)
