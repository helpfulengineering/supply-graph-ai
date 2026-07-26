---
title: The problem
reviewed: 2026-07-25
---

# The problem

Open hardware has a licensing story and a publishing story. What it does not have
is a manufacturing story.

A design is released under an open licence. The files are online. Anyone is
legally free to build it. And then, in practice, almost nobody does — because
finding someone who *can* build it is a research project every single time.

## Why closed supply chains don't have this problem

A large manufacturer knows exactly who can make each of its parts, because it
made that knowledge possible in advance. One organisation owns the designs, sets
the file formats, approves the suppliers, and keeps a single system of record.
Every part is described the same way. Every supplier's capabilities are recorded
in the same vocabulary. The question *who can make this?* is a database query.

None of that is a technical achievement. It's an organisational one. It works
because somebody had the authority to make everyone describe things the same way.

Open hardware has no such authority — and shouldn't. That's the point of it.

## What that costs

Without a shared way of describing things, four problems compound.

**Designs are described inconsistently.** One project publishes a bill of
materials as a spreadsheet, another as a wiki table, another as a paragraph of
prose. One says "3mm acrylic", another says "3 mm PMMA sheet", another shows a
photograph. All three mean the same thing. No software can tell.

**Facilities are described inconsistently, when they're described at all.** A
makerspace lists its equipment on an about page. A university lab has an internal
spreadsheet. A small manufacturer has a brochure. Nobody publishes capabilities
in a form another system can read.

**Nothing connects the two.** Even where good design data and good facility data
both exist, they live in separate worlds with no common vocabulary.

**So the knowledge stays in people's heads.** Ask around long enough and someone
will know a workshop that could help. That works at the scale of one person's
network, and fails at every larger scale — and it fails completely at the moment
you need it most, when the person who knew is unavailable and the timeline is
hours.

## Why this is the hard part

Most of Open Hardware Manager is not the matching. It's the **normalisation** —
the unglamorous work of turning wildly heterogeneous descriptions into one
consistent format that can actually be reasoned about.

That is deliberate, and it follows from a principle we try to hold to: **meet
people where they already are.** The alternative — demanding that every project
and every workshop adopt our format before they get any value — is how you build
a system nobody uses. Open hardware's diversity is not a defect to be corrected.
It's the condition the software has to work under.

So OHM absorbs the mess. It reads designs in the formats people already publish,
and reads facility data from directories that already exist, and does the
translation itself.

## What this doesn't fix

Normalisation can only work with what it's given. If a design doesn't say what
it's made of, no amount of processing will invent that. If a workshop's public
listing says what the space is *about* but not what it can *make*, OHM inherits
that limit.

This is the honest constraint on everything else here, and it's why the quality
of what facilities and designers contribute matters more than any algorithm we
could write. See [what's built and what isn't](../reference/whats-built.md) for
where that currently bites.
