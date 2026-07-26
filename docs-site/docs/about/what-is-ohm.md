---
title: What is OHM?
reviewed: 2026-07-25
---

# What is OHM?

This problem is already solved. Just not for us.

Inside a closed supply chain, one company owns the designs, the file formats, and
the system of record. Ask it who can build part 47-B and it answers instantly,
because every part and every supplier lives in one system that one organisation
controls.

Open hardware has no owner and no shared format. The designs are scattered across
repositories, wikis, forums, and PDFs, described however their author felt like
describing them. The workshops that could build them are scattered too. So the
most basic question in the field — *who can make this?* — has gone largely
unanswered for years.

Open Hardware Manager is an attempt to answer it.

## What it actually does

OHM keeps structured records of two things: **open hardware designs**, and **real
production facilities** — makerspaces, fab labs, university workshops, small
manufacturers. It works out which of those facilities can build a given design,
and hands you what you need to go and ask them.

That's it. OHM is a way of finding out who can make the thing. It is not a
marketplace, a shop, or a broker: the conversation that follows happens directly
between you and the workshop.

## A real example

Take the [High-Clearance Face Shield](https://3d.nih.gov/entries/3dpx-014582), a
design published on the NIH 3D Print Exchange during the COVID-19 pandemic — a
face shield with enough frontal clearance to be worn over dental loupes.

It is in OHM's catalogue. Ask OHM who can build it, anywhere, and the answer is
unhelpfully large: thousands of workshops, because the design needs 3D printing
and a great many places have a 3D printer.

Ask a better question — *who can build it in France?* — and OHM returns more than
250 named workshops: GraouLab, SimplonLab, Villette Makerz, Humanlab, and
hundreds more, each one a real place with a real address that a person could
contact today.

That second question is the one worth asking, and before OHM there was no
practical way to ask it.

## What this is for

Three things follow from being able to ask that question.

**Anyone can produce open hardware.** A design that only its author can
manufacture is not really open. Knowing who *else* can build it is what makes
the licence mean something in practice.

**Mutual aid becomes possible under pressure.** In a crisis you cannot build this
network — there is no time to find workshops, agree formats, and establish trust
while people are waiting. The network has to already exist. Everyday use is what
makes it exist.

**Nobody has to depend on us.** OHM is open-source software you can run yourself,
on your own infrastructure, in your own jurisdiction, connected to whichever
other instances you choose. The version hosted at openhardwaremanager.org is a
convenience, not the product.

## Where to go next

- **[The problem](the-problem.md)** — why open hardware in particular has resisted
  this for so long, and what has to happen before any of it works
- **[How it works](how-it-works.md)** — the moving parts, in plain terms
- **[Is OHM for you?](is-ohm-for-me.md)** — what it offers a university lab, a
  community workshop, or an organisation that needs to run its own
- **[What's built and what isn't](../reference/whats-built.md)** — an honest,
  automatically generated account of what works today
