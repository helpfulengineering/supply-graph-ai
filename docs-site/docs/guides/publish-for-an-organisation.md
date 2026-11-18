---
title: Publish for an organisation
area: identity
surface: web
---

# Publish for an organisation

An organisation on a node is a **space**: a named identity with an admin. The
admin affiliates people. Affiliated people publish designs (and facilities) on
the organisation's behalf. The publisher signs; the organisation's key is
never used for that claim.

## Administer affiliations

If you administer an organisation, open **People → Organisations**. Each
organisation you administer is a section: affiliate by person DID, then renew
or unaffiliate from each member row.

```bash
ohm identity affiliate add did:key:zPerson --space did:key:zOrg
ohm identity affiliate renew GRANT_ID
ohm identity affiliate revoke GRANT_ID
```

The affiliation **expires**. Renewal is the admin's act. A lapsed affiliation
stops **new** records naming the organisation; records that were valid when
signed stay as they were.

You do not need to be a node admin or a coordinator to do this — only the
organisation's admin. Coordinators manage invites and the member inventory;
they do not affiliate people. See [Manage people](manage-people.md).

## Publish a design on its behalf

If an organisation's admin has affiliated you, you can publish a design for
it. The picker is labelled **On behalf of**.

- One affiliation is selected for you, including when you save from Generate.
- With several, you choose.
- None is allowed — publishing without an org is always fine.

How to get a design into the node at all is still
[Add a design](add-a-design.md). This page is only the organisation part.

You sign the design. The organisation is not part of the design's content
hash, so the same bytes published by two people still match.

A node that syncs the design shows the organisation as **verified** when it
can check the evidence chain as of the moment you signed, and **unverified**
when it cannot. Unverified means this node could not prove the claim — not
that the design is deleted.

You can add or remove the organisation later, from the design, from your
account, or with:

```bash
ohm okh attribute
```

Adding it requires a **current** affiliation. Removing it does not. A
facility uses the same idea: `ohm okw attribute`.

## Curated lists for an organisation

An organisation's admin can publish a curated list for that organisation.
Private or members-only designs are refused, so a list never widens who can
see a record. How lists work on a node — publish, subscribe, superseded and
removed marks — is under
[Run your own node → Curated lists](run-your-own-node.md#curated-lists).

## Related

- [Manage people](manage-people.md) — invites, coordinators, member inventory
- [Join a node](join-a-node.md) — registering as a member
- [Who can see your data](who-can-see-your-data.md) — visibility levels
