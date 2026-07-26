---
title: Add a design
area: okh
surface: web
---

# Add a design

Getting an open hardware design into OHM, so that people who aren't you can find
out they could build it.

There are three ways in. Pick by what you already have.

## From a repository URL — start here

If your design lives in a public GitHub or GitLab repository, point OHM at it and
let it read the documentation into a structured record. You review and correct
what it found, then keep the result.

This is the right default for almost everyone, and the only sensible approach if
you have more than a handful of designs.

→ **[Import a design from a repository URL](import-from-a-url.md)**

## From a file you already have

If your design is already described in a standard format — an OKH manifest, or
an OKH-LOSH file — OHM can read it directly, with no extraction and no guessing.
This is the highest-fidelity route, because nothing is being inferred.

Organisations with a whole collection in some other structured format are a
slightly different case, usually solved with a converter written for that
format.

→ **[Bring your organisation's collection into OHM](bring-your-collection.md)**

## By hand

**Designs** → **New design** takes a design record as JSON, which you can paste
or upload. It validates before saving.

Being straightforward about this: it expects you to already know the OKH format,
which most people reasonably don't. It exists for people working directly with
the data — and as the fallback when the other two routes don't fit.

If you're hand-authoring, use the URL import on any similar public project first
and look at what comes out. A real example is a faster way to learn the shape
than a specification.

!!! note "A friendlier form is coming"

    A guided structured editor for designs — like the one the URL import already
    uses for review — is planned. Until then, hand entry means JSON. See
    [what's built and what isn't](../reference/whats-built.md).

## What makes a design useful once it's in

Whichever route you took, the same handful of fields decide whether OHM can do
anything with it:

**Manufacturing processes.** Without these, a design can't be matched to
anything. This is the single highest-value field.

**Materials.** What it's made of, as specifically as the documentation supports.

**Function and description.** What the thing does — how a person decides whether
it's what they were looking for.

**Licence.** What others may actually do with it. An open design with unclear
licensing is a design people hesitate to build.

You can add a design with the bare minimum and improve it later. A thin record
that exists beats a perfect one that doesn't.

## What happens next

Once a design is in, you can [find who can build it](find-who-can-build-it.md),
or [bundle it into a package](share-as-a-package.md) to hand to a workshop.
