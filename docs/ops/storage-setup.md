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
supply-trees/   saved match solutions
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
Already present (4):
  - okh/
  - okw/
  - packages/
  - supply-trees/
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
  "prefixes_found": ["okh/", "okw/", "packages/", "supply-trees/"],
  "prefixes_created": [],
  "total_found": 4,
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
`OHM_STORAGE_CONFIG_PATH`. It is read at boot **before** the storage service is
configured, and takes precedence over the environment.

It cannot live in the object store like every other credential OHM holds:
credentials for the new provider would be written into the old one and orphaned
the moment the switch took effect, leaving an instance that can neither reach
its backend nor read the configuration that would explain why. Mount the
directory as a volume and configuration survives a container replacement.

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

## What happens to the data already there

Switching points the instance at a new backend and leaves the old data where it
is — invisible, but intact. That is one of three answers, and `--mode` picks
which (#381).

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
switch with `--mode migrate` first, confirm the new one is serving, then wipe
separately.

**Over the API, migration runs as a job.** A copy of a populated backend takes
far longer than an ingress timeout allows, and a caller that cannot observe it
cannot tell a slow copy from a stalled one. `POST /api/storage/config` with
`"mode": "migrate"` returns a job id, and `GET /api/storage/migration/{job_id}`
reports cumulative progress — the same event log the generation timeline uses.
Pass back `next_cursor` as `since` and only new events arrive.

The CLI runs migration in the foreground instead, printing each stage. A CLI
invocation is already a process the operator is watching, so a job would add a
broker dependency and a polling loop to buy nothing.

### abandon_and_wipe

Switch, then erase the old backend.

```bash
# See what would go, first. Nothing is switched and nothing is deleted.
ohm storage config set --provider local --bucket ~/new-data \
  --mode abandon_and_wipe --wipe-confirm /old/path --dry-run

# Then for real.
ohm storage config set --provider local --bucket ~/new-data \
  --mode abandon_and_wipe --wipe-confirm /old/path
```

**You must name the bucket being erased.** `scripts/clear_storage.py` protects
itself with an interactive "type DELETE to confirm" prompt, which does not
survive the trip to HTTP — and a boolean `confirm: true` is not a guard, it is
a checkbox a client sets by default. Echoing the exact bucket requires having
read what you are about to destroy. A mismatch deletes nothing **and switches
nothing**: "switched but not wiped" is a state nobody asked for, so the check
runs before anything happens.

The wipe runs **after** the switch has succeeded, never before. Erasing first
would open a window in which the old data is gone and the new backend has not
been proved — the one state there is no recovery from.

## A freshly installed node

`scripts/install.sh` starts a node on local storage under one mounted volume,
and mints the encryption secret without which the *first* configuration action
would fail — credential storage refuses to operate under the built-in default
keys, so a node installed without one starts, looks healthy, and cannot be
given storage credentials.

The volume covers both the object store and the configuration file, which is
why an upgrade keeps them:

```
<data dir>/objects   LOCAL_STORAGE_PATH        the object store
<data dir>/config    OHM_STORAGE_CONFIG_PATH   the configuration written here
```

The config file sits beside the object store rather than inside it. Inside, it
would be an object in the bucket it configures — listed, served, and erased by
a storage wipe.

