# Open Hardware Manager — developer docs

This is the **developer / agent corpus** (rationale, vocabulary, operational
judgment). Prefer source, OpenAPI (`/v1/docs`), and `--help` over prose that
narrates the tree. Prefer no doc over a stale one.

**User-facing product docs** live in [`docs-site/`](../docs-site/) — guides,
about pages, glossary. Do not mix the two.

Public glossary seed: [`CONTEXT.md`](../CONTEXT.md).

## Architecture (why)

* [Federation MVP ADR](architecture/federation-mvp-adr.md)
* [Facility claim ladder ADR](architecture/facility-claim-ladder-adr.md)
* [Process taxonomy ADR](architecture/process-taxonomy-adr.md)
* [File type taxonomy ADR](architecture/file-type-taxonomy-adr.md)
* [Identity model](architecture/identity-model.md)
* [Security modes](architecture/security-modes.md)
* [Source platforms](architecture/source-platforms.md)

## Ops (how we run / extend)

* [Federation infra](ops/federation-infra.md)
* [Heuristic rule design](ops/rule-design.md)
* [Release process](RELEASE.md)

## Adapters (intentional mapping contracts)

* [MSF datasheet](adapters/msf-datasheet.md)
* [OKH-LOSH TOML](adapters/okh-losh-toml.md)
