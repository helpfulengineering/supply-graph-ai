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

## Skills

- [Setup wizard](.claude/skills/setup/SKILL.md) — natural language setup, configuration Q&A, and documentation lookup for OHM
