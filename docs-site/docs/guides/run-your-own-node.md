---
title: Run your own node
area: selfhost
surface: selfhost
---

# Run your own node

OHM was built to be self-hosted. The instance we run is a convenience for people
who don't want to run software — it isn't the product, and nothing has to pass
through it.

If you're here because your organisation can't put its data on infrastructure it
doesn't control, this page is the answer to that.

## The fastest version

A published Docker image, no clone required:

```bash
docker run -p 8001:8001 \
  -e STORAGE_PROVIDER=local \
  -e LLM_ENABLED=false \
  touchthesun/openhardwaremanager:<version>
```

Your instance is now at `http://localhost:8001`. Interactive API documentation is
at `/v1/docs`, and `/health` reports what it's running and where its storage
points.

Images are published for both `linux/amd64` and `linux/arm64`, so this works on
Apple Silicon as well as x86 servers.

!!! tip "Pin a version"

    Published tags include specific versions, a floating minor, and `latest`.
    For anything you depend on, pin an explicit version rather than tracking
    `latest`, so an upgrade is a decision you make rather than one that happens
    to you.

## Storage

`STORAGE_PROVIDER=local` keeps everything on disk in the container, which is
right for trying it out and wrong for anything you care about, since the data
disappears with the container.

For real use, point it at object storage — Azure Blob, AWS S3, or Google Cloud
Storage are all supported. Each needs its provider's credentials passed as
environment variables, most conveniently through `--env-file`.

Because the provider is configuration rather than architecture, **where your data
lives is your decision, including which jurisdiction it sits in.** That is the
practical substance of the sovereignty claim elsewhere on this site.

## Configuration

Non-secret defaults live in per-environment configuration files chosen by an
`ENVIRONMENT` setting; anything passed as an environment variable overrides them.

Secrets — storage keys, API keys, any language-model credentials — are never in
those files. Pass them at runtime, through `--env-file` or your platform's secret
mechanism.

In production configuration, the application deliberately **fails to start** on
missing or invalid storage settings rather than coming up in a state where it
looks healthy and silently isn't.

## Getting an admin credential

A new instance has no users. You bootstrap the first credential by passing an
`API_KEYS` value at startup, then authenticate with it to create everything else.

Requests carry it as `Authorization: Bearer <token>`, the same way the CLI and the
web interface do.

## Federation is off by default

A fresh instance talks to nobody. It holds your records, serves your users, and
makes no outbound connections to peers.

Turn it on only when you actually intend to connect to other instances — at which
point you decide who to follow, and what leaves your instance, per record. See
[federation and sovereignty](../about/federation-and-sovereignty.md) and
[who can see your data](who-can-see-your-data.md).

## What running your own actually involves

Being straight about the commitment, because "self-host it" is easy to say:

- **Storage** you administer and back up
- **Upgrades** on your schedule — nobody pushes them to you, which is the point,
  but it does mean nobody pushes them to you
- **Access control** — who holds credentials on your instance
- **Federation decisions** — which peers to follow, and what to share

Beyond the initial setup this is ordinary web-service operation, not a
specialism. A team that already runs containerised services will find nothing
exotic here.

## Beyond the basics

Self-hosting also comes with tooling that doesn't live in the web interface —
scripts and make targets for setup, bulk import, and validation, plus the
day-to-day work of administering a federated instance. Those are documented in
the project's developer documentation rather than here.
