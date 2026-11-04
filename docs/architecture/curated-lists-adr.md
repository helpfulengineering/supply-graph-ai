# ADR: Curated lists as selective follow

## Status

Accepted. Publishing (#580) and subscribing (#581) are implemented. Keep-and-mark is not.

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

## Wire format

A published list is one signed document: the current membership. The signature
is Ed25519 over the canonical JSON of the fields below, hex-encoded, and the
signature is not part of that JSON. A peer checks it offline from
`publisher_did`, a `did:key`. This is the same construction as a catalog
record.

| Field | Meaning |
|---|---|
| `list_id` | Stable id of the list |
| `name` | Display name |
| `publisher_did` | DID whose key signed this document |
| `sequence` | Increases by one on every published edit |
| `entries` | The pins |

Each entry is a `content_hash` — the manifest content hash the catalog already
uses — and an optional `supersedes`, the content hash of the pin this entry
replaces. A removal is that hash no longer appearing in `entries`. Entries are
ordered by content hash in the signed JSON, so the signature does not depend
on insertion order.

A subscriber who misses a sequence can still check the current document. They
can link a pin only to the one named in `supersedes`.

`publisher_did` is the signer. A list a node publishes is signed by that
node's identity, the same key that signs its catalog records, and only a node
admin can publish it. A list an organisation publishes is signed by the space
key: `publisher_did` is the space DID, and the node makes that signature only
when the caller is the claimed admin. A peer checks one signature against
`publisher_did`. The space claim stays the separate fact of who the admin is,
and it is not part of the list signature. A shielded node can still publish,
because it holds the space key and does not need the admin's person key.

The hosting node does not sign the list. The subscription remembers which
node serves it, and that address is not part of the signed document. A host
that changes the document breaks the publisher's signature, and the subscriber
rejects it.

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
- **A node-signed envelope around the publisher's list.** The subscriber
  would also check that this particular node served those bytes, and the same
  document fetched from another node would fail that check. The subscription
  already records where to fetch the list.

## Consequences

- Closes the core of #134 (selective replication) without a general filter
  language.
- Collection zips stay for offline transfer and must carry provenance, so
  affiliation survives the trip.

## Related

- [Federation MVP ADR](federation-mvp-adr.md)
- [`members` visibility ADR](members-visibility-adr.md)
