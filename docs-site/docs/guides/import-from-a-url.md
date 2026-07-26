---
title: Import a design from a repository URL
area: okh
surface: web
---

# Import a design from a repository URL

Point OHM at a public GitHub or GitLab repository and it will read what's there
into a structured design record — then hand it to you for review.

This is the fastest way to get an existing project into OHM, and the main way an
organisation backfills a back catalogue without redocumenting years of work.

## Doing it

**Designs** → **Generate from URL**, paste the repository address, and generate.

Only the URL is needed. Everything else is decided for you.

Reading a repository can take **up to a minute** — sometimes longer for large
ones. The progress indicator is deliberately honest: it can't tell you how far
along it is, so it doesn't pretend. You can cancel at any point.

## Then review it — this part is not optional

What comes back is a **draft**, and treating it as finished is the main way to
get a bad record into the world.

Extraction reads what a repository actually says. Where documentation is
implicit, inconsistent, or absent, extraction is a best guess. The review step
exists because that guess needs a human.

The form is ordered by what actually needs your attention:

**Required** — title, version, function, documentation language, licensor, and
hardware licence. A design can't be downloaded until these are filled in. Any
that couldn't be extracted are marked.

**What drives matching** — manufacturing processes, materials, bill of
materials. These decide which workshops can build this, so they're worth more of
your time than anything else on the page. **Check the materials especially** —
they're the most error-prone part of extraction, and prose gets misread as
components more often than we'd like.

**Being found** — description, repository, keywords.

**Everything else** — collapsed, but present. Nothing extracted is hidden from
you.

Processes and keywords edit as removable tags. Nested structures like materials
and the bill of materials are shown as-is with a JSON editor, rather than a
half-built structured form that might quietly drop a field.

## Then download it

When the required fields are valid, download the design as a JSON file.

!!! note "Generated designs aren't saved to the catalogue"

    They're yours to download, not ours to keep. Without user accounts there's
    no owner and no provenance for a generated record, and adding unattributed
    records to a shared catalogue would degrade it for everyone. Saving arrives
    with accounts.

## When it doesn't work

**"That repository couldn't be read."** Private, misspelled, or moved. Only
public repositories work — private ones need credentials that belong to you,
which needs accounts.

**"The shared rate limit has been reached."** Everyone using the hosted instance
shares one quota for reading repositories, so heavy use by one person affects
others. Waiting is the fix. This goes away if you
[run your own node](run-your-own-node.md) with your own credentials.

**It read the repository but got little out of it.** That's a documentation
signal, not a failure. A repository that doesn't say what its parts are made of
gives extraction nothing to find. Fill in what you know and move on.

## A realistic expectation

Extraction on the hosted instance runs on rules rather than a language model.
It's fast, free, predictable, and works offline — and it's less clever than you
might expect. It finds what's stated plainly and misses what's implied.

That's the trade, and the guided review is how it's made to work. Assume you'll
correct something on every design, and it will rarely disappoint you.
