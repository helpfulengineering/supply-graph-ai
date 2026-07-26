---
title: How it works
reviewed: 2026-07-25
---

# How it works

Four steps, in plain terms. None of them require you to understand the formats
underneath.

## 1. Designs come in, however they're published

A design enters OHM from wherever it already lives — a repository, a published
manifest, a datasheet, a spreadsheet from an organisation's own archive. OHM
translates it into one consistent internal description: what the thing is, what
it's made of, what has to be done to produce it.

This is the step that makes everything else possible, and it's the one that does
the most work. See [the problem](the-problem.md) for why.

## 2. Facilities describe what they can make

A production facility — a makerspace, a university lab, a small manufacturer — is
described in the same consistent way: where it is, what equipment it has, what
processes it can perform, at what scale.

Some of that comes from directories that already exist, so many workshops are
already represented without having done anything. Some of it comes from
facilities describing themselves directly, which is richer, because a directory
entry says what a space is *about* while a facility can say what it can actually
*do*.

## 3. Requirements meet capabilities

Given a design, OHM works out what producing it requires, then finds facilities
whose capabilities satisfy those requirements.

It does this in layers, from strict to flexible: exact matches first, then
known-equivalent substitutions, then language-based understanding for
descriptions that don't line up neatly. Each result carries an explanation — not
just *this workshop matched*, but which requirements it satisfied, which it
didn't, and why.

The explanation matters as much as the answer. A confident-looking list of
workshops with no reasoning attached is not something you can act on.

## 4. The result is a supply tree

The answer is not always one workshop. When no single facility can perform every
process a design needs, OHM can plan across several: this component printed here,
that one laser-cut there, assembly somewhere else. That structure — the plan for
producing a design across one or more facilities — is what OHM calls a **supply
tree**.

This is what distributed manufacturing actually means in practice, and it's the
capability OHM is ultimately built around. It is implemented and it works, but be
aware of the limit today: multi-facility planning only helps when different
facilities have *different* gaps to fill. Where the facility data available to
OHM is thin in the same way everywhere — as it currently is for hand and bench
processes like soldering and assembly — there is nothing to combine, and results
come back as single-facility matches or as gaps.

That is a data problem rather than a design problem, and it's the strongest
reason for facilities to describe themselves properly. See
[what's built and what isn't](../reference/whats-built.md) for the current state.

## What happens next is up to you

OHM stops at knowing. It tells you which workshops can build your design, what
each one would contribute, and what's missing — and then you contact them.

There's no marketplace, no bidding, no commission, no account you have to
transact through. OHM is trying to end the ignorance, not to intermediate the
relationship.
