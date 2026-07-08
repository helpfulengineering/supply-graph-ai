# Fix proposal template

Status: **draft — awaiting human review**  
Probe: `<probe_module>`  
Generated: `<YYYY-MM-DD>`

## Problem (probe evidence)

Summarize what the probe observed in production/staging. Link harness JSON output
or paste key evidence (503 rate, latency ms, cache miss, broken file URLs).

## Root cause hypothesis

What we think is wrong (e.g. MatchingService cold init timeout, in-memory cache
on multi-replica ACA, raw GitHub URLs in OKH manifests).

## Proposed fix

Concrete architecture / code / infra changes. Keep scoped to one pain point.

## Scope

- [ ] Architecture / infrastructure
- [ ] Backend API
- [ ] Frontend UI
- [ ] Configuration / deployment (Azure Container Apps)

## Acceptance criteria

- [ ] Relevant probe passes against staging
- [ ] Regression test or synthetic journey covers the fixed path
- [ ] Operator doc updated if runbooks change

## Rollout / rollback

How to deploy safely and revert if needed.

## Review checklist

- [ ] Root cause confirmed (not just symptom)
- [ ] Fix approach agreed
- [ ] Owner assigned
- [ ] Ready for implementation issue

---
*Edit this template or auto-generated stubs under `docs/proposals/` before approving.*
