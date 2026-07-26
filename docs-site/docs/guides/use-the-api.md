---
title: Use the OHM API from your own software
area: api
surface: api
---

# Use the OHM API from your own software

Everything the web interface does, it does through a public HTTP API. Anything
you can do by clicking, your own software can do too.

## What you'd use it for

**Ask the matching question from somewhere else.** An inventory system, a
procurement tool, or an internal dashboard can ask "who can build this?" without
anyone visiting a website.

**Bring an existing collection in.** Organisations with a body of designs
already documented usually want them imported in bulk, not entered by hand.

**Keep another system in step.** Read the catalogue on a schedule and mirror the
parts you care about into your own tools.

**Build something we haven't.** The API is the same surface our own interface
uses, so nothing is held back for it.

## Finding your way around

Every running instance serves its own interactive documentation:

- `/v1/docs` — browsable API reference for the exact version that instance runs
- `/v1/openapi.json` — the machine-readable specification, for generating a
  client in your language

**Prefer those over any hand-written list**, including anything on this site.
They're generated from the running code, so they cannot be out of date in the way
prose can.

Endpoints live under `/v1/api/…`, grouped by the things you'd expect: designs,
facilities, matching, packages.

## Authenticating

Requests carry a bearer token:

```
Authorization: Bearer <your-token>
```

Read operations may be open depending on how an instance is configured. Anything
that writes needs a credential. On an instance you run, you create these
yourself — see [run your own node](run-your-own-node.md).

## Two things worth knowing before you build

**Match times vary enormously with scope.** An unfiltered match against the whole
network can take around a minute; a match narrowed by country typically returns
in seconds. Set your client timeouts with the slow case in mind, and pass filters
whenever you can — both for speed and because narrower results are more useful.

**Match responses include near misses.** The response contains facilities that
did not satisfy every requirement, alongside those that did, each with a
structured explanation of what was and wasn't met. Don't treat a confidence score
alone as "this workshop can build it" — read the explanation, which says which
requirements failed. See [find who can build a design](find-who-can-build-it.md).

## Which instance to point at

You can call the instance we host, and for trying things out that's the quickest
path.

For anything ongoing, run your own and point at that. You get your own data, your
own uptime, your own rate limits, and no dependency on a service you don't
control — which is the arrangement the whole project is designed around.

## The command line

There's also a CLI covering the same ground, which is often a better fit for
scripted imports and administration than driving HTTP directly. It's documented
with the project's developer documentation.
