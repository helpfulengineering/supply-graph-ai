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

Read operations are generally open. Writes are checked against the credentials an
instance is configured with — but note that **an instance started with no
`API_KEYS` configured accepts anonymous writes**, so on a node you run, setting
one is what turns write protection on. See
[run your own node](run-your-own-node.md#before-anyone-else-can-reach-it).

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

## Running a node just for the API

If you're embedding OHM rather than offering a web interface, the usual answer is
to start the stack without the frontend — `docker compose up ohm-api ohm-worker`,
covered in [run your own node](run-your-own-node.md#running-without-the-web-interface).

For the smallest possible footprint, a single container serves the API with no
Redis and no worker:

```bash
docker run -p 8001:8001 \
  -e STORAGE_PROVIDER=local \
  -e API_KEYS=<your-token> \
  touchthesun/openhardwaremanager:<version>
```

Know what you're trading away:

- **No background jobs.** `POST /api/okh/generate-from-url/jobs` returns an error
  saying jobs are disabled. Only the synchronous endpoint works.
- **Synchronous generation blocks for as long as it takes.** Small repositories
  return in seconds; a large, mature project can take several minutes, which will
  exceed default timeouts in most proxies and HTTP clients.
- **No shared cache**, so it doesn't scale past one container.

That makes it a reasonable fit for a sidecar serving small repositories, and a
poor one for anything pointed at repositories you don't control. If you're not
sure which you have, use the two-container form above.

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
