# Open Hardware Manager (OHM)

## Definition of done

Passing unit tests is **not** "ready to merge." Before claiming a change is
done, run `make ready` and show its output — it is the gate (format, lint,
tests, service↔API↔CLI parity, docs, live E2E), not a green pytest run.

A new or changed service is not done until its API endpoint, CLI command, and
docs land in the **same change**. If a service is intentionally not exposed,
record it as a row in `tests/parity/manifest.py` rather than leaving it
unaccounted for — `make parity` will fail until you do.

## Skills

- [Setup wizard](.claude/skills/setup/SKILL.md) — natural language setup, configuration Q&A, and documentation lookup for OHM
