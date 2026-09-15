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

### Take the list with you

Select the workshops you want and export them. You get a spreadsheet of who
matched and how to reach them — name, location, contact person, email, phone,
website — which you can sort, annotate, and share with people who have no OHM
account.

```bash
ohm match requirements design.okh.json --output matches.json
ohm match export-contacts matches.json --design "Ventilator" -o contacts.csv
```

`--format json` instead, if something downstream is reading it rather than a
person.

The export runs offline: it reads a match you already have and needs no server.
That is deliberate — the moment you most want a list of who can help is often
the moment connectivity is the problem.

**An export is a snapshot.** The design and the time of the match are written
into the file header and its filename, because facilities change. Two exports
taken a week apart can be compared directly to see which workshops dropped off
the list — `diff`, or two columns in a spreadsheet.

### Asking for a quote

Select the workshops and generate a request for quotation — one document each,
addressed to that workshop, naming what matched and what did not.

**Download the bundle**, and you get a zip holding those documents plus the
design package they refer to: everything to attach to an email and send. The
recipient needs nothing from OHM. They have never heard of it, and the documents
do not ask them to visit it — the design is in the attachment, not behind a link.

Fill in your name and email when you generate, and the RFQ says who is asking
and where the quote should go. Leave them out and it says to reply to your
message, which is true anyway: you are the one sending it.

!!! note "Who may build a bundle"

    Assembling a bundle builds the design package if one does not exist yet, so
    it needs a write key by default. An instance that wants outreach to be a
    public act can allow anyone to do it by setting
    `RFQ_BUNDLE_REQUIRE_AUTH=false`. Previewing the documents never needs a key
    either way — that only formats what you already have.
