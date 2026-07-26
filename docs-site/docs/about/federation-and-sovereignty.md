---
title: Federation and sovereignty
reviewed: 2026-07-25
---

# Federation and sovereignty

OHM is **federated**. That means there is no central OHM that everyone connects
to. There are many instances, each holding its own records, each choosing who it
talks to.

If you've used Mastodon or Matrix, this is the same idea. If you haven't, it
comes down to two questions your instance answers for itself.

## Who do you listen to?

Your instance holds designs and workshops. You choose which other instances to
follow, and their records flow into your view.

Nobody appoints those peers. There is no registry deciding which instances are
legitimate, and no application to be approved. You follow who you have reason to
trust, and stop when you don't.

## Who can see yours?

Every record you hold has a visibility setting, and you decide what leaves your
instance — and how much of it.

That last part matters more than it sounds. Visibility isn't only on or off: a
workshop can be visible to peers you've chosen while its address stays private.
Being findable and being exposed are different things, and a system that
conflates them isn't safe for the people using it.

## What that looks like in practice

A group of universities each run their own instance and follow one another. A
student searching for a machine sees every workshop across the whole consortium —
not because those labs registered with anyone, but because they chose to be
visible to each other.

Nothing about that arrangement requires us. If our instance vanished tomorrow,
theirs would carry on.

## Why sovereignty follows

Put those two questions together and you get the thing institutions actually
need: **no required intermediary.**

Your records live on infrastructure you control, in the jurisdiction you operate
under. You are not asking permission, not subject to a platform's terms changing,
and not exposed to a service you depend on being discontinued or acquired. The
software is open source; if you disagree with where the project goes, you can run
what you have indefinitely.

This is why federation was brought forward in the project's development rather
than left as a later refinement. It isn't a feature bolted onto a hosted service.
It's the part that makes the hosted service optional.

## Where we run, and why

We host an instance at openhardwaremanager.org so that people who don't want to
run software can still use OHM. Being straightforward about it:

**It runs on Microsoft Azure, in the `westus3` region.** Not a strategic choice —
a supporting NGO has cloud credits there and it was the fastest route to
something people could actually use. OHM is built to be portable and ships
configurations for other providers, so this is a fact about our circumstances
rather than about the software.

If that's not acceptable for your organisation's data, the answer isn't for us to
justify it. The answer is that you run your own, which is what the whole design is
for.

## Choosing peers

For now, sensible defaults. Deliberately curating a set of peers matters once
groups of institutions start joining as groups, and we'd rather build that when
there are real consortia to shape it than guess at it in advance.
