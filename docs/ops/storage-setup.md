# Storage setup

Setting up storage means three things, in order: connect to the provider, prove
the connection actually works, and establish the top-level prefixes OHM reads
from. One function does all three, and every entry point calls it.

## The prefixes

Four, established with a `.gitkeep` placeholder each:

```
okh/            designs
okw/            facilities
packages/       built packages
```

No structure is enforced beneath them. OHM searches recursively from each root,
so you may organise files under these prefixes however you like.

## Running it

Any of these do the same work:

```bash
# CLI, the usual way
ohm storage setup --provider local --bucket ~/ohm-data
ohm storage setup --provider gcs --bucket my-bucket --region us-central1
ohm storage setup --provider azure_blob --bucket my-container
ohm storage setup --provider aws_s3 --bucket my-bucket --region us-east-1

# Machine-readable
ohm storage setup --provider local --bucket ~/ohm-data --json

# Standalone, for bootstrapping an environment that has credentials but no
# installed app. Same arguments, no dependency on the rest of the stack.
uv run python scripts/setup_storage.py --provider gcs --bucket my-bucket
```

## What "verified" means

Setup does **not** report success until it has written an object to the backend,
read it back, compared the bytes, and deleted it.

This matters because connecting is not the same as working. A client can be
constructed, and credentials can authenticate, against a bucket that does not
exist or that the caller may not write to. Only a round trip tells you.

It is also why setup does not go through `StorageService.configure`. That
function **swallows connection failures on purpose**, so the API process can
start in a degraded state and serve reads rather than refusing to boot. Setup
inheriting that was a real bug: pointed at an unusable backend it printed

```
✅ Storage directory structure created successfully!
Created 0 directories:
```

and exited 0. It now fails loudly and exits non-zero, with the provider error
attached.

## Running it twice

Safe, and a no-op the second time. Setup probes for each placeholder and skips
the ones already present, so re-running does not restamp established
directories with a fresh `created_at`.

The output distinguishes the two cases, which is the point — "nothing to do"
and "nothing done" look identical otherwise:

```
✅ Storage is ready.
Provider: local
Location: /home/you/ohm-data
Already present (3):
  - okh/
  - okw/
  - packages/
Nothing to do — storage was already set up.
```

## JSON output

`--json` reports what was found separately from what was created:

```json
{
  "status": "success",
  "provider": "local",
  "bucket": "/home/you/ohm-data",
  "storage_location": "/home/you/ohm-data",
  "verified": true,
  "prefixes_found": ["okh/", "okw/", "packages/"],
  "prefixes_created": [],
  "total_found": 3,
  "total_created": 0
}
```

`directories_created` and `directories` are also present, carrying the created
prefixes under their previous names for callers that already read them.

## Where the code lives

`src/core/services/storage_setup.py` — `setup_storage(config)`, returning a
`StorageSetupResult` and raising `StorageSetupError` when the backend cannot be
reached or written to.

The CLI command, the CLI helper module and `scripts/setup_storage.py` are thin
callers with no storage behaviour of their own. They used to each carry a copy,
and the copies had drifted: one created three prefixes rather than four, one
restamped placeholders on every run, and two reported success on backends they
had never reached.


## Changing the backend after installation

Setup establishes a backend. Changing which backend an instance uses, while it
is running, is the storage-configuration API (#377).

This exists because installation and configuration are separate. A hands-off
installer cannot ask for storage credentials before the instance is up, so
storage has to be configurable once it already is.

```bash
# What am I running on?
ohm storage config show

# Switch. Existing data stays where it is.
ohm storage config set --provider local --bucket ~/ohm-data

ohm storage config set --provider azure_blob --bucket my-container \
  --credential account_name=myaccount --credential account_key=secret
```

Over the API, admin only:

```
GET  /v1/api/storage/config
POST /v1/api/storage/config
```

### Validate first, commit second

A new backend is proved before anything is committed: connect, write a probe
object, read it back, then validate or initialize the directory structure.
Only then is the configuration persisted and the running service swapped.

**A rejected configuration changes nothing.** This is the point of the
ordering rather than a nicety. `StorageService.configure` swallows connection
failures so the app can boot degraded, and it replaces the active manager
before connecting — so a mistyped credential, applied directly, would leave an
instance with no working storage *and no route back*, because the endpoint that
would fix it needs storage-backed admin credentials to authenticate.

A misspelled credential name is rejected too, rather than dropped, so the
failure arrives at the point of the typo instead of as an authentication error
later.

### Where the configuration lives

An encrypted file, by default `~/.ohm/storage-config.json`, overridable with
`OHM_STORAGE_CONFIG_PATH`. The installer and the compose files both point it at
`/app/storage/config/storage-config.json`, on the mounted volume. It is read at boot **before** the storage service is
configured, and takes precedence over the environment.

It cannot live in the object store like every other credential OHM holds:
credentials for the new provider would be written into the old one and orphaned
the moment the switch took effect, leaving an instance that can neither reach
its backend nor read the configuration that would explain why. Mount the
directory as a volume and configuration survives a container replacement.

The file may sit inside the object root — the compose files do exactly that, with
one volume for everything. It is still never an object: the local storage provider
refuses any key that names it, and does not list it, so a migrate, a backup or a
wipe cannot carry it (or the node's identity keys) anywhere. The same protection
covers a custom `OHM_FEDERATION_DATA_DIR` and any layout that puts either inside the
object root; a layout that keeps them outside it has nothing to protect.

The file is `0600` inside a `0700` directory, and credential values are
encrypted with the same `OHM_ENCRYPTION_*` material as LLM provider keys.
**Persisting credentials under the built-in default encryption keys is
refused** — that key ships in the source tree, so encrypting with it is
obfuscation rather than protection. A configuration carrying no credentials
(`local`, or a cloud provider using ambient instance credentials) has nothing
to protect and is allowed either way, which keeps a development instance
workable before a secret has been minted.

If the file is unreadable, carries an unknown schema version, or was encrypted
with material that has since changed, it is ignored and the instance falls back
to its environment configuration, with the reason logged. A node that will not
start is worse than one running on the settings it was deployed with.

### Who learns of a switch

Three kinds of process can be involved, and they do not all hear about it:

- **The API** reads the saved configuration file at boot, before it configures
  storage (`main.py`). A switch made **through its own API** (the panel, or
  `POST /api/storage/config`) is applied at once, in that process.
- **The CLI is a separate process.** `ohm storage config set`, in any mode, runs the
  switch inside the CLI process: it saves the configuration, but a running API is not
  told and **keeps serving from the old backend until it is restarted**. Shown with
  two real processes: after a CLI switch the running API still reported the old
  bucket as both its configuration and what answered, while the saved file named the
  new one. Restart the API to apply a command-line switch.
- **The worker** (the compose files and the Azure deployment; not the installer) does
  not read or write the object store at all. `generate_from_url`, its only task, has
  no storage calls, and nothing under `src/core/generation` touches it. It connects a
  backend from its own environment when a service initialises, but no job uses it, so
  a backend change does not affect background jobs. If a task ever starts using the
  object store it would take its storage from that environment, never from the saved
  file.

A running API therefore cannot see that its saved configuration has changed, and
`GET /api/storage/config` reports the live bucket for both "configuration" and "what
answered" in that state.

### Checking whether a restart is pending

```bash
ohm storage status
```

reads two things and shows both: the saved configuration, and — separately — a
local heartbeat marker the API writes beside it (`api-live.json`) while it is
running. This is a file read, not an HTTP call: the CLI has no way to
authenticate to the API, so it cannot just ask.

```
$ ohm storage status
Storage status
  saved:  azure_blob (new-container) [persisted]
  live:   running — local (~/ohm-data), heartbeat 2.1s ago, pid 4821 on api-1
  note:   the running API is on a different backend than the saved
          configuration — a restart is pending to apply it.
```

The marker reports one of three states:

- **running** — a fresh heartbeat. Also reported for a marker that cannot be
  read or parsed at all: an unreadable marker must never look safer than a
  readable one, so it fails closed rather than being treated as absent.
- **stale** — the heartbeat has not been refreshed for three intervals
  (~45s by default; `OHM_STORAGE_MARKER_HEARTBEAT_SECONDS` tunes the interval,
  mainly for tests). The process behind it is gone — `kill -9`, an OOM kill, a
  host crash — without running its clean-shutdown path.
- **absent** — no API has started since the marker was last removed. A clean
  shutdown (the normal path: SIGTERM/SIGINT, `docker stop`, a rolling restart)
  removes it; a killed process leaves it to go stale on its own.

`ohm storage status --forget` clears a marker the status output already shows
as stale. It refuses while the marker still looks running — including an
unreadable one, for the same fail-closed reason — so it cannot be used to paper
over an API that is, in fact, still there.

The marker is node-local state, like the saved configuration and the identity
keys beside it: the local provider refuses to list, read, or write it as an
object, so nothing that walks the store (a migrate, a backup) can see it.

### One switch at a time

A restart is **pending** precisely when a *running* API's marker names a
different backend than the saved configuration — the state the box above
labels with `note:`. `ohm storage config set` (any mode) refuses to run while
one is pending, from either the CLI or the panel/API's own inline switch:

```
$ ohm storage config set --provider local --bucket ~/newer-data
❌ A restart is already pending: the API has been serving local (~/ohm-data)
   since 2026-09-20T18:40:17+00:00, but the saved configuration is
   azure_blob (new-container). Restart the API to apply that change before
   switching again — one change at a time, so a second switch cannot be
   lost underneath the first.
```

Without this, a second switch made before the first was ever applied would
overwrite the *saved* configuration — the first switch's target is gone the
moment the second one is written, and the running API, which never saw
either, would apply only the second at its next restart. Restart to clear the
pending state, then switch again.

Both `GET /api/storage/config` and `/health` carry the same picture for
anything watching over HTTP: a `runtime` block (`GET /api/storage/config`) or
a `restart_required` flag inside the `storage` block (`/health`, which needs
no admin credentials — the marker read behind it never touches storage
itself, so it is as safe to expose as the rest of `/health`).

Every successful switch or migrate — from the CLI — ends with a boxed
reminder, so the next step is never left implicit:

```
┌─────────────────────────────────────────┐
│ Restart the API to apply this change.   │
│ It is still serving local (~/ohm-data). │
└─────────────────────────────────────────┘
```

or, when no API is running to restart:

```
┌───────────────────────────────────────────────────────────┐
│ The next API start will apply this — none is running now. │
└───────────────────────────────────────────────────────────┘
```

## What happens to the data already there

Switching points the instance at a new backend and leaves the old data where it
is — invisible, but intact. That is one of two answers, and `--mode` picks
which (#381). A third, `abandon_and_wipe`, has been retired (see below).

### abandon (the default)

Leave it. Nothing is copied and nothing is erased.

```bash
ohm storage config set --provider local --bucket ~/ohm-data
```

### migrate

Copy everything to the new backend, verify it, and only then switch.

```bash
ohm storage config set --provider azure_blob --bucket new-container \
  --mode migrate --credential account_name=acct --credential account_key=secret
```

**The order is a safety property.** Validate the destination, copy, verify the
copy, and only then swap. The instance keeps serving from the old backend for
the whole copy, so a migration that fails partway — or that you abandon — leaves
a working instance on its original storage and a partial copy on the
destination. That is recoverable. Swapping first is not.

Verification re-reads every object at the destination and compares its digest
to the source. That doubles the reads, which is the right trade for a one-time
move whose failure mode is silent data loss.

The copy is provider-agnostic: it uses only list, get and put from the storage
abstraction, so any supported provider can be migrated to any other.

Migration does **not** erase the source. If you want the old backend emptied,
migrate first, **restart the API** (a command-line switch does not reach a running
one), confirm the new backend is serving, then wipe separately.

**The running node keeps writing to the old backend until it restarts.** Anything
written between the start of the copy and the restart is not in the new backend, and
an object deleted in that window stays in it, because the copy never carries
deletions over. Restart straight after migrating, and stop whatever writes to the
node first if the move must be complete.

**Over the API, migration is retired (#543).** `POST /api/storage/config` with
`"mode": "migrate"` answers 400 and points at the CLI; nothing is enqueued and
nothing changes. The job it used to enqueue could never find the storage it was meant
to copy from (it built a fresh, unconfigured `StorageService` per task, so it stopped
with `There is no current storage to migrate from`), nothing called it, and it carried
the destination's credentials through Redis as cleartext JSON.

The CLI runs migration in the foreground instead, printing each stage. A CLI
invocation is already a process the operator is watching, so a job would add a
broker dependency and a polling loop to buy nothing.

### abandon_and_wipe (retired)

This mode switched and then erased the old backend in one step. It has been retired
(#543), over both the CLI and the API, and now answers with an explanation and changes
nothing.

Run from the CLI, it erased whatever the *CLI process* believed was the current
backend, while a running API kept serving from that backend until it restarted, and
had no way to know. Shown with a live API holding one design: after
`--mode abandon_and_wipe --wipe-confirm <old>` the API's design count went from 1 to
0 and the file was gone. The CLI's switch never reaches a running API, so that window
is guaranteed, not rare.

The replacement is a standalone, guarded `ohm storage wipe` (#547) — its own
step, taken after a restart rather than folded into the switch itself.

### wipe

```bash
ohm storage wipe --provider local --bucket ~/old-data --wipe-confirm ~/old-data
```

Same echo guard as before (name the bucket you are erasing, exactly, or nothing
happens) and the same `wipe_storage` from #381 — what changed is *when* it can
run. It refuses when the target is anything a boot or a running process might
still need:

- **a restart is pending** (#545) — the node's own picture of its storage is
  already out of date; resolve that first.
- **the saved configuration** — what the next boot applies.
- **the environment-configured backend**, when there is no saved configuration
  (a fresh process without one would use it, so it is exactly as live as a
  saved one).
- **what a running API's marker says it is live on** (#544), by provider and
  bucket. An unreadable or ambiguous marker refuses *regardless* of the
  target — the same fail-closed rule the marker itself follows, since it
  cannot be ruled out. A marker gone **stale** does not refuse; that is what
  staleness means. `ohm storage status --forget` clears a marker you have
  confirmed is dead sooner than waiting out the interval, but staleness alone
  already unblocks the wipe.

```
$ ohm storage wipe --provider local --bucket ~/old-data --wipe-confirm ~/old-data
❌ Refusing to wipe: a running API (heartbeat 2.1s old) is still serving from
   '~/old-data'. Switch it elsewhere and restart first.
```

`--dry-run` reports what would be destroyed and deletes nothing, same as
before. The documented sequence: switch or migrate, **restart the API**,
confirm it is healthy on the new backend, then wipe the old one.

`scripts/clear_storage.py` remains for development resets, which is a
different case entirely — there is no "old backend" to protect when the whole
point is emptying the one in use.

## A freshly installed node

`scripts/install.sh` starts a node on local storage under one mounted volume,
and mints the encryption secret without which the *first* configuration action
would fail — credential storage refuses to operate under the built-in default
keys, so a node installed without one starts, looks healthy, and cannot be
given storage credentials.

The volume covers the object store, the configuration file, and the node's
identity keys, which is why an upgrade keeps them:

```
<data dir>/objects     LOCAL_STORAGE_PATH        the object store
<data dir>/config      OHM_STORAGE_CONFIG_PATH   the configuration written here
<data dir>/federation  OHM_FEDERATION_DATA_DIR   the node's identity and its
                                                 people's signing keys
```

The config file sits beside the object store rather than inside it. Inside, it
would be an object in the bucket it configures — listed, served, and erased by
a storage wipe.

The identity keys are on the volume for a different reason. Left at its default,
`OHM_FEDERATION_DATA_DIR` resolves under the container user's home directory,
which the image does not create, so minting an identity fails. Creating that
directory by hand is worse than the failure: the keys then live inside the
container, while the space claim they sign for is stored on the volume. After the
next upgrade the claim names an admin whose key no longer exists.

