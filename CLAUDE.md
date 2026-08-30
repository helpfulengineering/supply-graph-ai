# Open Hardware Manager (OHM)

## Definition of done

Passing unit tests is **not** "ready to merge." Before claiming a change is
done, run `make ready` and show its output — it is the gate (format, lint,
tests, service↔API↔CLI parity, docs), not a green pytest run.

A new or changed service is not done until its API endpoint, CLI command, and
docs land in the **same change**. If a service is intentionally not exposed,
record it as a row in `tests/parity/manifest.py` rather than leaving it
unaccounted for — `make parity` will fail until you do.

## Measuring against a server

`make ready` and `frontend-ready` start their own servers and are safe to trust.
Anything you run by hand against `localhost:5173` is not, because Playwright's
`reuseExistingServer` attaches to whatever is already there.

**Before blaming the code for a test result, confirm the environment under test
is the one you think it is.** Two specific traps, both of which have produced
failures that read as regressions and were not:

- **A build under a running server.** `next build` rewrites `.next` in place; a
  server already serving it answers with a mix of old and new. A hook now blocks
  this (`.claude/hooks/no-build-while-serving.sh`), but the shape generalises to
  anything that regenerates what a running process is reading.

- **Cold versus warm servers in a before/after comparison.** `next dev` compiles
  routes on first hit, so a cold server under parallel load times out across
  unrelated specs — 35 failures in one run here, none of them real. A
  measurement is only a comparison when both sides had the same warm-up. Warm
  the server with one discarded run, then measure.

When a result is surprising, re-run it against a server you started yourself
before reasoning about the diff.

## Orientation

There is no generated index of this codebase, deliberately. One existed
(`.repo-map.md`) and was retired: at 139k tokens it could not be read, it
covered no TypeScript, and it truncated the symbol lists that mattered — while
costing a merge conflict on every concurrent PR, because a file derived from
the whole tree changes whenever anything does. `rg`/`grep` answer "where is X"
faster, exactly, and in every language. What follows is the part grep cannot
tell you.

**Layout.** Backend Python in `src/core/` — `api/routes` and `api/models`
(request/response), `services/` (the work), `storage/` (object-store planes),
`models/` (domain), `federation/`, `packaging/`. CLI in `src/cli/`, one module
per API surface. Web UI in `frontend/` (see `frontend/AGENTS.md`). Tests split
by kind under `tests/`: `unit`, `api` (contract, mocked service), `integration`
(in-process ASGI, real storage), `federation`, `parity` (the ratchets). `docs/`
is published; `notes/` is gitignored planning.

**Gates.** `make ready` (13 steps) and, for anything touching `frontend/`,
`cd frontend && npm run frontend-ready`. Both start their own servers.

**Parity is a ratchet, not a lint.** A new API endpoint must either be called by
the frontend or get a row in `tests/parity/manifest.py` classifying why not; a
new top-level frontend route must be declared in that area's `fe_routes`. The
row for a planned-but-unbuilt call is backlog, and the commit that wires the
call deletes it.

### Invariants that bite

These are load-bearing, non-obvious, and each has already caused a real defect.

- **`to_dict()` is a whitelist.** It drops `ohm_*` keys, so OHM-internal
  metadata (creator account, creator DID) rides the *stored dict*, never the
  parsed model. Anything reading attribution must read it off the raw storage
  entry, before parsing. This is also why content hashes are safe: every
  `manifest_content_hash` caller hashes a `to_dict()` projection, so authorship
  cannot enter the hash and the same design by two authors still dedups. If you
  add a caller that hashes a raw stored payload, that invariant breaks.

- **Record lists are viewer-scoped.** `list(viewer=...)` returns shareable
  records plus the caller's own; `admin` buys nothing extra. `viewer=None` means
  *unscoped* and exists for trusted internal callers only — the federation
  catalogue builder and the CLI. A request handler that lists without a scope
  serves every private record on the node to anyone who asks;
  `tests/parity/test_viewer_scope_ratchet.py` fails the build if one does.

- **Visibility and provenance are their own planes**, keyed by record id in the
  object store, deliberately outside the manifest and outside the content hash.
  New records stamp `private`; a record with no visibility object is legacy and
  resolves to `followers`, which is why old catalogues did not empty.

- **Most of the identity surface is `require_admin`.** A registered non-admin can
  call `whoami` and the public security policy, and little else. Check the
  dependency before assuming an operation is available to an ordinary user.

- **Credential material shares the object store** with records, under `auth/`.
  Anything that migrates, copies or wipes storage is moving or destroying keys
  too.

## Skills

- [Setup wizard](.claude/skills/setup/SKILL.md) — natural language setup, configuration Q&A, and documentation lookup for OHM
