---
title: Who can see your data
area: identity
surface: web
---

# Who can see your data

If you're putting a workshop's address into someone's software, you're entitled
to know exactly what happens to it. This page is that answer.

Two controls do the work: **visibility**, which decides *whether* a record leaves
this instance and to whom, and a **disclosure profile**, which decides *how much
of it* goes.

## Visibility: whether, and to whom

Every record has one of three settings.

| Setting | What happens |
|---|---|
| **Private** | The record stays on this instance. Nothing is exported to anyone. |
| **Followers** | Shared with peer instances that this one has chosen to connect to. |
| **Public** | Available to anyone who asks this instance for its catalogue. |

**New records are private.** Nothing is shared because you created it — sharing
is a decision you make afterwards.

## Disclosure profiles: how much

This is the part that matters most, and the part most systems get wrong. Being
findable and being exposed are different things, and OHM treats them separately.

A record is split into groups, and you choose which travel, per audience:

| Group | Contains |
|---|---|
| **Identity** | Name and status — **always included** |
| **Location** | Address, access details, loading dock |
| **Equipment** | Machines and tools |
| **Operations** | Hours, contact, capacity |
| **Supply** | Materials and products |

You set these separately for **followers** and for **public**. So a workshop can
be publicly discoverable — visible on the map, matchable by capability, showing
its equipment and processes — while its **address is shared only with peers you
trust**, or with nobody.

The default is deliberately conservative: identity only, unless you say
otherwise.

## Seeing what others see

The sharing panel shows a **preview of what a given audience will actually
receive**, built from your current settings. Use it before publishing, rather
than reasoning about what should happen.

Where visibility is private, the preview says so plainly: nothing is exported.

## What this doesn't cover

**Anyone who has already received a record has it.** Federation is
copy-based — if a peer synced your record while it was public, tightening the
setting later stops future sharing but doesn't reach back. This is true of
anything published anywhere; it's worth being conscious of before publishing an
address, not after.

**Other instances make their own choices.** This instance honours your settings.
An instance run by someone else holds their own copy under their own operator's
control. That's the trade federation makes: no central authority means no central
enforcement either. It's why *who you choose to federate with* is a real
decision — see [federation and sovereignty](../about/federation-and-sovereignty.md).

**Records you didn't create.** If a workshop's details came from a directory
where the space published them itself, that publication is theirs and continues
regardless of anything set here.

## If you need more control than this

Run your own instance. Then the records never leave your infrastructure at all
unless you export them, and jurisdiction is whatever you decide it is. See
[run your own node](run-your-own-node.md).
