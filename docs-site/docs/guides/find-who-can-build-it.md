---
title: Find who can build a design
area: match
surface: web
---

# Find who can build a design

The central thing OHM does: take a design, and tell you which workshops could
produce it.

## Running a match

Go to **Match**, pick a design, and run it.

Before you do, **narrow the network** — by country, city, region, process, or
source. This matters more than it looks:

- **The results get useful.** Asking who can build something *anywhere* often
  returns thousands of workshops, which is not an answer to any real question.
  Asking who can build it *in Belgium* is.
- **It's dramatically faster.** An unfiltered match against the whole network can
  take around a minute. A filtered one typically returns in a few seconds.

## Reading the results

Each result is a workshop, with a confidence badge (High / Medium / Low and a
percentage) and the first line of an explanation.

**Read the explanation, not the percentage.** Every result opens to a breakdown
of which requirements the workshop satisfied, which it didn't, and why — for
example that it covers the printing and cutting a design needs but has nothing
recorded for soldering.

### Near misses, and how much slack to allow

A workshop that satisfies most of a design's requirements but not all of it is
often still worth contacting — a single missing process is frequently an easy
gap to fill. So results say plainly what is missing rather than reducing it to a
score: **"Missing 1 of 4 requirements"**, or **"Meets every requirement"**.

A slider controls how much slack to allow, measured in missing requirements
rather than a percentage — one gap means something quite different in a design
with two requirements than in one with six. It starts at a single gap, and it
cannot be relaxed past the point where a result would meet fewer than two of
your requirements.

## When nothing matches

Usually one of three things.

**A required process is missing everywhere.** Bench processes — soldering,
assembly, drilling — are barely represented in the facility data OHM currently
has. A design needing them can come back empty even where workshops could
plainly do the work. This is a data gap, not a judgement about those workshops.
See [what's built and what isn't](../reference/whats-built.md).

**Your filter is too tight.** Widen from city to country and try again.

**The design doesn't say enough.** If its documentation never records what it's
made of or how it's produced, there's nothing to match against. OHM can only
work with what a design actually states.

## When one workshop isn't enough

Where no single workshop can perform every process, OHM can plan across several —
one part printed here, another cut there. That plan is a **supply tree**, and
it's what distributed manufacturing means in practice.

Be aware of the current limit: this only helps when different workshops have
*different* gaps. Where the available data is thin in the same way everywhere, as
it is today for bench processes, there's nothing to combine and results come back
as single workshops or as gaps.

## What happens next

You contact the workshops. OHM tells you who and why; the conversation is yours.

Generating a formal request for quotation is built but not yet available in the
web app.
