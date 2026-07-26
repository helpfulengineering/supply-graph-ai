---
title: OKH and OKW
---

# OKH and OKW

You can use OHM without ever meeting these two names. They appear here because
you'll eventually see them in an export, an API response, or a conversation, and
it's better to know what they are than to guess.

They're the two data standards OHM is built on. One describes **a thing that can
be made**. The other describes **a place that can make things**.

---

## OKH — Open Know-How

**Describes a design.** What it is, what it's for, what it's made of, what files
exist, what has to be done to produce it, and under what licence.

If you've ever tried to build someone else's project and found the documentation
scattered across a repository, a forum thread, and a video, you already
understand the problem OKH addresses. It's an attempt to say: here is a
consistent way to describe a hardware design, so that both a person and a
computer can work out what building it would involve.

For OHM this is the format everything gets translated *into*. A design arrives
in whatever shape its author published it, and becomes an OKH record. That
translation is most of what OHM does internally.

### A note on versions

You may see **OKH-LOSH** alongside plain OKH. LOSH is the more developed line of
the standard, and in May 2024 the Internet of Production Alliance re-incorporated
it as the official successor to the original OKH v1. It has been maintained by
Open Source Ecology Germany, and grew out of work in the INTERFACER project.

Practically: if someone hands you an OKH-LOSH file, OHM can read it.

---

## OKW — Open Know-Where

**Describes a facility.** Where it is, what equipment it has, what processes it
can perform, at what scale, and how to make contact.

The insight behind it is that "where can this be made?" is a question nobody had
a shared vocabulary for. Plenty of directories list workshops; almost none of
them record capability in a form another system can act on. OKW is an attempt at
that vocabulary.

OKW is also where OHM's current limits bite hardest. The standard can express
considerably more than most facility records actually contain — see
[what's built and what isn't](whats-built.md).

---

## Why two standards rather than one

Because they change independently, and are maintained by different people who
know different things.

A design's description is authored once by whoever published it, and is mostly
stable. A facility's description belongs to that facility, changes when they buy
or retire a machine, and is nobody else's to write. Keeping them separate means a
workshop can improve its own record without touching anybody's designs, and vice
versa.

Matching is the operation that brings them together: requirements on one side,
capabilities on the other.

---

## Where they come from

Both are stewarded by the **Internet of Production Alliance**, an organisation
working on open, interoperable infrastructure for distributed manufacturing.
Neither is OHM's invention — we're an implementer, not the author, and we'd
rather these standards outlive any particular piece of software including ours.

See [standards and ecosystem](standards-and-ecosystem.md) for how these fit
alongside the other projects in this space.
