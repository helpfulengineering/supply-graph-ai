---
title: Bring your organisation's collection into OHM
area: convert
surface: api
---

# Bring your organisation's collection into OHM

For organisations that already have a body of open hardware designs — a
university's project archive, an NGO's field equipment documentation, a
programme's accumulated output — and want it discoverable rather than entered by
hand.

If you have five designs, add them individually. This page is for the case where
you have two hundred.

## The realistic picture

There is no single import button, and honestly there can't be one, because
collections don't arrive in a single format. What actually happens is one of
three things, in descending order of how easy your life will be.

**Your data is already in a format OHM reads.** If your designs are published as
OKH-LOSH manifests, conversion is a solved problem — there's a converter, and it
runs over a batch without anyone writing new code.

**Your data is structured but in a format of your own.** This is the common case
for organisations that documented things properly before any standard existed.
Your spreadsheet or database is perfectly good; it just isn't a format anything
else speaks. Here we typically write an adapter for your format specifically.
That has been done before — the datasheet converter in OHM exists because
Médecins Sans Frontières documents its open hardware work in a particular
internal way, and meeting that where it was proved easier than asking an
organisation to redocument years of work.

**Your data is unstructured.** Documentation in prose, PDFs, or scattered wiki
pages. Extraction can get part of the way, but expect review rather than a clean
import.

## Why we write adapters rather than asking you to convert

It would be simpler for us to publish a format and ask everyone to produce it.
It also wouldn't work — see
[meet people where they already are](../about/meet-people-where-they-are.md).

An organisation with two hundred documented designs has already done the hard
part. Asking them to redo it in our shape, before they've seen any benefit, is
how a project ends up with excellent tooling and no users.

## What building an adapter involves

Concretely, if your format needs one:

**What we'd need from you**

- A representative sample — a dozen records covering the messy cases, not the
  tidiest ones
- What the fields mean, particularly anything domain-specific. Field names are
  rarely self-explanatory across organisations
- Which fields matter to you. Not everything needs to map, and pretending
  otherwise slows things down
- Someone who can answer questions about the data as they arise

**What you'd get**

- A converter from your format to OKH, runnable repeatedly, so this is an
  ongoing pipeline rather than a one-off migration
- Your designs in the catalogue, matchable against facilities
- The converter itself, in the open, so anyone with a similar format benefits

**What to expect around ambiguity.** Real collections always contain records that
don't quite fit — missing versions, ambiguous licences, files referenced but
never published. We'd rather flag those for review than silently guess, so
expect a list of things needing a human decision. That list is a feature.

## Doing it yourself

If you'd rather not involve us: conversion and creation are available through
the API and the command line, so a technically comfortable team can write their
own adapter against the same interfaces we would.

The CLI is usually the better fit for bulk work — see
[use the OHM API](use-the-api.md).

!!! note "There's no bulk import in the web interface yet"

    Batch import currently runs through the API, the command line, and
    purpose-built scripts. A web interface for it is planned and would make this
    considerably more approachable. See
    [what's built and what isn't](../reference/whats-built.md).

## Before you start

Two decisions worth making deliberately.

**Where it goes.** If your organisation has any constraint about where its data
lives, decide that before importing rather than after. Running your own instance
means the collection is yours end to end — see
[run your own node](run-your-own-node.md).

**Who sees it.** Imported records follow the same visibility rules as anything
else, and default to private. You can bring a collection in, look at it, and
decide about sharing afterwards. See
[who can see your data](who-can-see-your-data.md).

## Getting in touch

If you have a collection and want to work out which of the three cases you're
in, get in touch. The answer is usually apparent from a handful of sample
records.
