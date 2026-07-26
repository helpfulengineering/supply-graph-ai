---
title: Meet people where they already are
reviewed: 2026-07-25
---

# Meet people where they already are

This is the principle that shapes most of OHM's design, and it's worth stating
plainly because it explains a lot of otherwise odd decisions.

**The alternative approach is to define the correct format and require everyone
to adopt it.** It's tempting, because it makes the software much simpler. It also
doesn't work. Open hardware has no central authority that could compel adoption,
and a system that delivers nothing until the world reorganises itself around it
will be waiting a long time.

So OHM absorbs the mess instead of legislating against it. That shows up in two
places.

## Designs: read what people already publish

Open hardware projects describe themselves however suits them — repositories,
wikis, PDFs, spreadsheets, structured manifests, prose. OHM's job is to read what
exists and translate it into something consistent, rather than to insist on a
format before it will help you.

This is most of the work. See [the problem](the-problem.md).

## Workshops: read the directories that already exist

There are already people who have done the difficult, unglamorous work of mapping
where workshops are: Maps of Making, and others we intend to add. Rebuilding
those from scratch would be wasteful and slightly insulting.

So OHM reads them, and shows a **union** of what it finds, with the ability to
filter by source. A workshop that appears in one of those directories is already
in OHM without having done anything or agreed to anything with us.

It's worth being precise about how that data works, because it's easy to assume
the worst. In the case of Maps of Making, each space publishes a small file **on
its own website**, and the map is assembled by finding those files. The
information belongs to the space and is hosted by the space. The map — and OHM —
are readers.

So this is not a case of workshops being scraped into someone else's database.
It's a case of workshops publishing about themselves, and more than one thing
being able to read it. That's the arrangement we want to support and extend, not
replace.

## The honest cost of this approach

Reading what already exists means inheriting its limits.

If a directory records what a space is *interested in* rather than what it can
*produce*, OHM inherits that gap and cannot invent the difference. If a design's
documentation never says what it's made of, no amount of processing will
determine the material.

That is the real constraint on how well OHM works today, and it can't be
engineered away — it can only be addressed at the source, by workshops describing
themselves more fully and by the directories that carry that information being
able to express it.

Which means the useful work is often not in our code at all. It's in improving
shared vocabularies, contributing back to the projects whose data we rely on, and
making it worth a workshop's time to say more about itself.
