---
title: Standards and ecosystem
---

# Standards and ecosystem

OHM didn't invent the standards it runs on and doesn't own the data it reads. It
sits among a number of projects that each solve a different piece of this
problem. Knowing who does what makes it much clearer what OHM is actually
contributing — and what it would be presumptuous of us to claim.

## The standards

**Open Know-How (OKH)** — a way of describing a hardware design. Described by the
Internet of Production Alliance as "an open data model for sharing hardware
designs and documentation online, to know how something can be made." Maintained
by the Internet of Production Alliance together with Open Source Ecology Germany.

**OKH-LOSH** — the more developed line of that standard. It grew up within the
INTERFACER project and was maintained by Open Source Ecology Germany; in May 2024
the Internet of Production Alliance re-incorporated it as the official successor
to OKH v1. This is the version most actively used.

**Open Know-Where (OKW)** — the equivalent for facilities: where things can be
made, and what those places can do. Also from the Internet of Production
Alliance.

OHM implements both. See [OKH and OKW](okh-and-okw.md).

## Directories of workshops

[**Maps of Making**](https://mapsofmaking.org) — a map of makerspaces and
workshops, and currently the source of most facilities visible in OHM.

Its design is worth understanding, because it's unusually good: each space
publishes **its own data at its own endpoint**, which the map reads. The data
belongs to the space and is hosted by the space; Maps of Making reads it, and so
does OHM.

It builds that on standards rather than inventing them. Spaces publish
[SpaceAPI](https://spaceapi.io/), the format a few hundred hackerspaces already
serve, and the map stores what it reads as linked data queryable over SPARQL.
That is why the arrangement extends: anything able to serve a file at a URL can
be a source, which is how an OHM facility can appear on the map — see [publish
to Maps of Making](../guides/publish-to-maps-of-making.md).

Alongside those spaces it keeps its own vocabulary of maker activities, and it's
worth being straight about its limitation, since it shapes what OHM can currently
do. That vocabulary describes what a space is *about* — digital fabrication,
electronics, 3D printing — rather than the specific processes it can perform.
Useful for finding spaces; only partly sufficient for working out who can build a
given design. Improving this is a conversation with the people who maintain it,
not something OHM should paper over on its own.

Other directories exist and we intend to read them too. The aim is a union of
what's out there, filterable by source — not a replacement for any of it.

## Certification

**OSHWA certification**, run by the Open Source Hardware Association, gives
producers "an easy and straightforward way for producers to indicate that their
products meet a uniform and well-defined standard for open-source compliance."

Worth being clear about what that is and isn't, because the names sound adjacent:
OSHWA certification concerns whether a project is genuinely open — its licensing,
documentation, and branding. It says nothing about whether anyone near you can
build it. That second question is the one OHM exists for. The two are
complementary rather than competing.

## Where OHM fits

The short version: **the standards describe, the directories collect, and OHM
connects.**

More precisely, OHM contributes three things and tries not to claim more:

1. **Translation** — reading designs published in whatever form their authors
   chose and turning them into consistent records. Most of the engineering.
2. **Matching** — working out which facilities' capabilities satisfy a design's
   requirements, and explaining the reasoning.
3. **Federation** — letting instances hold their own data and share it on their
   own terms, so none of the above requires a central authority.

What OHM deliberately does *not* try to be is the owner of the standards, the
maintainer of the directories, or the arbiter of who is legitimate. Those jobs
belong to other people who are doing them well, and a distributed manufacturing
network that quietly centralised on us would have failed at its own premise.

---

*Descriptions of other projects on this page are drawn from their own published
material and may fall behind changes they make. Where accuracy matters, their
documentation is authoritative and ours is not.*
