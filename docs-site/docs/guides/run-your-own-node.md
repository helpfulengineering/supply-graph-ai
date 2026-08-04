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

## Start it

```bash
git clone https://github.com/helpfulengineering/supply-graph-ai.git
cd supply-graph-ai
docker compose up
```

That's the whole thing. The web interface is at `http://localhost:8080`, and the
API is at `http://localhost:8001`.

No configuration file is needed to start. Published images are pulled rather than
built, so the first run is a download rather than a compile, and they're built
for both `linux/amd64` and `linux/arm64` — Apple Silicon included.

!!! note "Requires Docker Compose 2.24 or newer"

    Older versions fail to parse the file. `docker compose version` tells you
    what you have.

### What you just started

| Container | Does what |
|---|---|
| `ohm-frontend` | the web interface, and proxies the API so the browser sees one origin |
| `ohm-api` | the HTTP API |
| `ohm-worker` | runs imports in the background |
| `redis` | queues that work and caches results |

Four containers, one command. The worker is the reason
[importing from a URL](import-from-a-url.md) can run as a background job with
real progress instead of blocking an HTTP request — see
[running without the web interface](#running-without-the-web-interface) for why
that matters more than it sounds.

## Before anyone else can reach it

**A node with no `API_KEYS` set accepts anonymous writes.** Anyone who can reach
the port can create and delete designs. That is fine on a laptop and dangerous on
a public IP.

Set a credential before the node is reachable by anyone but you:

```bash
echo "API_KEYS=$(openssl rand -hex 32)" >> .env
docker compose up -d
```

Requests then carry it as `Authorization: Bearer <token>`, the same way the CLI
and web interface do. This is also how you bootstrap the first credential on a
new instance: there are no users yet, so `API_KEYS` is what you authenticate with
to create everything else.

Redis is deliberately **not** published to your host — nothing outside the stack
needs it, and an unauthenticated Redis reachable from the internet is a
well-known way to lose a server. The optional metrics container isn't started at
all unless you ask for it, and listens only on localhost when you do.

## Configuration

Everything else is optional. Copy the template when you want to change something:

```bash
cp env.template .env
```

Non-secret defaults live in per-environment configuration files chosen by an
`ENVIRONMENT` setting; anything in `.env` or passed as an environment variable
overrides them.

Secrets — storage keys, API keys, language-model credentials — belong in `.env`
or your platform's secret mechanism, never in the configuration files.

### Storage

The default keeps everything on disk in a Docker volume, which is right for
trying it out and wrong for anything you care about.

For real use, point it at object storage — Azure Blob, AWS S3, and Google Cloud
Storage are all supported, each needing its provider's credentials in `.env`.

Because the provider is configuration rather than architecture, **where your data
lives is your decision, including which jurisdiction it sits in.** That is the
practical substance of the sovereignty claim elsewhere on this site.

In production configuration, the application deliberately **fails to start** on
missing or invalid storage settings rather than coming up in a state where it
looks healthy and silently isn't.

### A language model, if you want one

OHM works without one; you'll notice its absence in exactly one place, and
[Configure an LLM](configure-an-llm.md) covers the whole picture — including
running a local model with ollama and no cloud key at all.

Nothing needs enabling first. Add a provider key, through **Settings → LLM
providers** or `.env`, and it is used.

### Running in production

Set `ENVIRONMENT=production` and the node requires two more values before it will
start — `LLM_ENCRYPTION_SALT` and `LLM_ENCRYPTION_PASSWORD`, which encrypt stored
provider credentials. They're required whether or not you use a language model.
[Configure an LLM](configure-an-llm.md#running-in-production) explains why.

## Running without the web interface

To embed OHM in something you already run, start the API and worker and skip the
interface:

```bash
docker compose up ohm-api ohm-worker
```

Redis starts automatically because both depend on it. You get the full API at
`http://localhost:8001` with background imports working, and no web UI.

**Keep the worker even though nothing visible uses it.** Without it, importing
from a URL falls back to running inside the HTTP request — and on a real project
that takes minutes, not seconds. One mature repository we test against takes
around seven minutes, which is past nginx's default proxy timeout and most HTTP
client defaults. The worker is what makes import survive contact with a large
repository.

If you want the API without Redis at all, a single container works for small
repositories — see [using the API](use-the-api.md#running-a-node-just-for-the-api)
for that recipe and its limits.

## Federation is off by default

A fresh instance talks to nobody. It holds your records, serves your users, and
makes no outbound connections to peers.

Turn it on only when you actually intend to connect to other instances — at which
point you decide who to follow, and what leaves your instance, per record. See
[federation and sovereignty](../about/federation-and-sovereignty.md) and
[who can see your data](who-can-see-your-data.md).

## Running it somewhere other than your laptop

Compose is the supported path everywhere, including on a server. A VM with Docker
installed runs the same four containers with the same command — put a reverse
proxy in front for TLS, set `API_KEYS`, and you have a node.

**On Azure**, there's a managed alternative: Container Apps with a provisioned
Redis, worker, and secrets, described in
[Deploy a node on Azure](deploy-a-node-on-azure.md). It is one option rather than
the blessed path — we maintain it because it's what the public instance runs.

**On AWS and Google Cloud**, S3 and Cloud Storage are supported as storage
backends today, and you configure them in `.env` like any other provider. There
is no equivalent managed-compute deployment for either; run Compose on an EC2
instance or Compute Engine VM. We'd rather say that plainly than imply a
cloud-agnostic deployment story we haven't built.

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

!!! tip "Pin a version"

    Compose pins the image tag to a specific release, so an upgrade is something
    you choose. `OHM_VERSION=0.10 docker compose up` follows patch releases
    within a minor version instead.

## Beyond the basics

Self-hosting also comes with tooling that doesn't live in the web interface —
scripts and make targets for setup, bulk import, and validation, plus the
day-to-day work of administering a federated instance. Those are documented in
the project's developer documentation rather than here.

Developers changing OHM itself want `docker compose up --build`, which builds the
images from your working tree instead of pulling them.
