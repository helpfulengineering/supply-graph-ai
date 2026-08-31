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
