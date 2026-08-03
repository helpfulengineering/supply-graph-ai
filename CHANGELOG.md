# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.10.6] - 2026-08-03

### Added

- **`make secrets-check`** confirms the API and worker container apps agree on
  every secret they share — storage key, both git tokens, and all three Redis
  URLs — by comparing digests, never values. The deploys mirror these on every
  run, so this verifies that took effect and catches what mirroring cannot: a
  half-completed deploy, or a secret edited by hand afterwards. A `job-broker-url`
  mismatch is the one that matters: jobs are then accepted and never consumed,
  with nothing wrong-looking in either app. Kept out of `make ready`, which must
  stay runnable offline.
- **The Celery worker rolls with every release.** `release.yml` deploys the
  worker **before** the API — consumer before producer, both pinned to the same
  published digest — so the API never enqueues work a stale worker might
  mishandle, and the two can never run different code. The worker has no ingress,
  so its post-deploy check compares the active revision's image digest against
  what was just published. The end-to-end job probe runs as the release's final
  gate: the only check that proves the whole path rather than that containers
  rolled over. Pipeline ordering and gating are asserted by tests, since a
  mis-ordered rollout fails silently — jobs succeed and return wrong manifests.
- **Async generate-from-url enabled in production**, with an end-to-end health
  probe. `jobs_enabled = true` in the production config; the job endpoints leave
  their 503 branch once the worker is deployed. `probe_async_generation` submits
  a real job, polls to a terminal state, and fails if it does not complete —
  distinguishing *accepted but never consumed* (no worker on the queue) from
  *ran but did not finish*, because the fixes differ. This is the worker's health
  signal: platform probes are HTTP/TCP only, and a wedged worker still answers
  `celery inspect ping` while consuming nothing. Ops guide:
  `docs/ops/async-generation.md`.
- **`staging` environment.** `config/environments/staging.toml` describes a
  full-fidelity rehearsal of production — same image, same server, same Redis
  instance — isolated by blob container (`staging`) and Redis database index
  (3/4/5 vs production's 0/1/2) rather than by separate infrastructure. It pins
  `USE_GUNICORN=true` because the entrypoint's `auto` mode starts
  `uvicorn --reload` for any non-production environment, which would make the
  rehearsal meaningless. Async jobs are enabled there first.
  `deploy_azure.py --mirror-secrets-from <app>` stands up a new environment by
  copying the shared secrets from an established app, and `--target-port`
  (default 8001, the port the image actually binds) makes a created app
  reachable. Without the flag the production deploy is byte-for-byte unchanged.
- **Celery worker deploy for Azure Container Apps.**
  `deploy/scripts/deploy_azure_worker.py` deploys the worker as its own
  no-ingress container app running the same image in `worker` mode. Its env
  comes from the shared config surface — top-level settings plus `[worker.env]`
  — so the storage target is declared once and the API and worker cannot drift;
  `[worker]` holds the deploy shape (1 vCPU / 2Gi, one replica, concurrency 1).
  The storage key and git access tokens are **mirrored from the API app** on
  every deploy rather than set by hand, so the copies cannot diverge. Secrets
  ride inline on create (an app that does not exist yet cannot have secrets set
  on it) and are set ahead of the update otherwise; logged commands redact
  secret values. Deploying a worker does **not** enable async jobs.
- **Redis connection secrets minted by the deploy.** The backend deploy reads the
  Redis access key from Azure and mints `cache-redis-url`, `job-broker-url`, and
  `job-result-backend` as Container App secrets on every deploy, from the
  non-secret `[redis]` coordinates in `config/environments/<env>.toml` (cache
  db 0, broker db 1, results db 2). Azure is the single source of truth for the
  credential: rotating the key needs no repo change and apps sharing the
  instance cannot drift apart. URLs carry `?ssl_cert_reqs=required` (kombu
  silently parses a bare `rediss://` URL as `CERT_NONE`) and percent-encode the
  key (base64 keys contain `/` and `+`, which truncate an unencoded URL).
  Async jobs stay **off** — `JOBS_ENABLED` is unchanged.
- **Ingress-less Container Apps in the shared Azure deployer.** `ServiceConfig`
  gains `ingress_enabled`, `command`, and `args`, so one deploy path now covers
  background workers as well as web services: create omits the ingress flags and
  no FQDN lookup is attempted (an app without ingress has none, and querying for
  one failed deploys that had actually succeeded). `get_status` reads the FQDN
  from the response it already has instead of a second lookup. Web-service argv
  is pinned by regression tests — the API and frontend deploys are unchanged.
## [0.10.5] - 2026-08-02

### Added

- **Admin-managed LLM provider credentials.** Encrypted keys can be set,
  rotated, tested, and deleted via `PUT/GET/DELETE /api/llm/credentials/{provider}`
  (strict admin auth) and **Settings → LLM providers**. Keys hot-swap into the
  running `LLMService` without a restart; storage refuses default encryption
  salts/passwords. Env vars remain a fallback at startup.
- **Celery worker foundation for async jobs.** `celery[redis]` dependency,
  `src/core/jobs/` Celery app + `generate_from_url` task, Docker entrypoint
  `worker` mode, and `ohm-worker` + always-on Redis in `docker-compose.yml`.
  Config: `JOBS_ENABLED`, `JOB_BROKER_URL`, `JOB_RESULT_BACKEND`.
- **Async generate-from-url job API + CLI.** `POST/GET /api/okh/generate-from-url/jobs`
  accepts one or many URLs (one Celery job each), with per-IP rate limiting,
  concurrent/queued caps, and optional auth for LLM-enabled runs
  (`GENERATE_FROM_URL_REQUIRE_AUTH_FOR_LLM`). CLI: `ohm okh generate-jobs
  submit|status|wait`.
- **Weighted progress for async generation.** `GenerationEngine` and
  `OKHService.generate_from_url` emit stage/fraction updates (clone → layers →
  BOM → quality); Celery tasks forward them via `update_state` so job polls
  can drive a real progress bar.
- **Generate UI uses async jobs.** `/okh/generate` accepts comma-separated URLs,
  submits Celery jobs, polls with real progress bars, and cancels via job
  revoke — no longer blocked by the 120s nginx proxy timeout.
- **Azure Terraform: optional Redis + Celery worker.** `ohm_node` can provision
  Azure Cache for Redis and a no-ingress worker Container App (`enable_jobs`).
  `environment=production` auto-provisions `LLM_ENCRYPTION_*` secrets so stored
  LLM credentials are not encrypted under default keys.

### Removed

- **Seven catalogue designs whose file references were exclusively Google Drive
  viewer pages.** No file type is recoverable from those URLs, so the designs
  could never be classified and matched nothing — noise in every result set.
  Their source URLs are recorded in the removing PR; all were generated from a
  URL and can be regenerated. Also removed four integration-test fixtures
  (`licensor: "Test Suite"`) that were live in the production catalogue.
### Added

- **`sewing` process** (Wikidata Q652122). The taxonomy had 48 processes and
  none could describe sewn work, so the COVID-response textile PPE in the
  catalogue — gowns, scrubs, masks — was *unclassifiable*, not merely
  unclassified. Deliberately top-level rather than a child of `assembly`: the
  hierarchy is consulted during matching, and a metal-fabrication shop
  advertising "assembly" cannot sew a surgical gown.

### Fixed

- **`ohm okh infer-processes --all` now scans everything.** It defaulted to
  `--limit 100` and the service capped an unlimited run at 500, so against 175
  designs it reported `scanned=100` and looked complete — a partial backfill
  presented as success. `--limit` is now an opt-in cap, and a capped run says
  how many manifests it left behind.

### Fixed

- **Process inference now reads TSDC codes**, the DIN SPEC 3105 codes a design's
  own manifest declares. It previously read only design-file extensions and the
  title, so **123 of 175 catalogue designs carried no manufacturing processes at
  all — and a design with no processes returns zero matches.** Inference was
  riding on a filename convention: designs *titled* `3DP-…` got `3D Printing`,
  while an identical `tsdc: ['3DP']` on `3D-Simple-Bias-Tape-Maker` got nothing.
  The taxonomy already resolved these codes; only inference never asked. A
  dry-run backfill over production fills 100 of the 123 (81%).

### Fixed

- **Match results contradicted themselves.** A fully successful match was
  presented as a total failure: a `coverage 0/3` headline and a warning-styled
  "Coverage gaps" banner naming the exact processes the design needs, sitting
  above ten facilities each reading "Meets every requirement". The summary read
  `tree.capabilities_used`, a field that is present on every tree and **always
  empty**, so nothing was ever counted as matched — every match reported zero
  coverage. It now reads the matcher's own per-requirement verdict, the same
  evidence the cards show.
- **Requirement counts were doubled.** A design declaring a process in both
  `manufacturing_processes` and `manufacturing_specs.process_requirements` — all
  19 of the 100 designs sampled that have both — had each requirement counted
  twice, so a three-requirement design reported six and the near-miss slider
  offered to relax to four. A duplicate counts as matched only if every copy
  did, so deduping cannot hide a gap.
- **One confidence figure per result.** Cards showed "confidence 100%" beside
  text reading "(confidence: 95%)". These are different fields: the former is
  coverage-derived and reads 1.0 whenever everything matched, the latter is the
  mean of the per-requirement confidences. The card now shows the figure with
  per-requirement evidence under it.

### Fixed

- **A configured but unusable Redis now falls back to the memory cache.** Every
  Redis operation reports a miss on failure, so a broken instance cached
  *nothing* while reporting `backend: redis` — strictly worse than the memory
  backend it replaced, which at least caches per replica. Production ran a full
  deployment in that state: the connection URL still contained the literal
  `<key>` placeholder, so every request paid full assembly (single-design fetch
  1.5s against a 0.23s warm path). The backend is now verified with a PING
  before it is committed to.
- **Redis provisioning docs no longer hand-substitute the access key.** The
  commands read and percent-encode it themselves, and the page says how to
  confirm the cache actually works — `backend: redis` alone is exactly what a
  completely non-functional cache reports.

### Changed

- **The catalogue cache is shared across replicas in production**
  (`cache_backend = "redis"`). Assembling every OKH manifest once is what made
  the Designs page fast, but the memory backend caches it *per replica*, so each
  instance pays a full assembly on its first request and scaling out returns
  whoever lands on a new replica to the slow path — visible in production as a
  4.19s outlier among otherwise sub-second fetches. Requires a Redis instance and
  the `CACHE_REDIS_URL` secret; see `docs/testing/cache-deployment.md`.

### Fixed

- **Every "View supply tree" link on the match page 404'd.** The card linked by
  *tree* id, but the route it lands on loads
  `/supply-tree/solution/{id}/visualization`, which only accepts a *solution* id.
  Confirmed against production: a tree id returns 404 where the solution id
  returns 200. Cards now link by solution id.
- **A match saved only the best result's tree**, discarding the other nine, so
  even a corrected link could not have shown most facilities' trees. The saved
  solution now carries every returned tree; each becomes a node in the
  visualization bundle.
- **An unreachable Maps of Making could produce 504s on unrelated matches.** A
  failed refresh left the cache empty, so every later request re-attempted the
  fetch and, serialized on the cache lock, queued behind the one in flight —
  callers crossed nginx's 120s `proxy_read_timeout`. A failure now suppresses
  retries for 60s, a caller holding stale data no longer waits for an in-flight
  refresh, and the fetch ceiling drops from 30s to 15s (production measures ~2s
  for 3,193 spaces).
- **The prefilter's no-overlap fallback ignored its candidate cap**, the one path
  by which an entire network could reach heavy matching unbounded. It is taken
  by every electronics design, since MoM advertises zero facilities for
  soldering, assembly and drilling.

- `CACHE_BACKEND=redis` without `CACHE_REDIS_URL` now logs an error and falls
  back to the memory cache instead of raising. The two settings are applied by
  different mechanisms — one is checked-in config, the other a secretRef — so a
  deploy can legitimately land one before the other, and misconfiguring a
  performance optimisation should not fail every cached request.
- The Redis client's socket timeout is now sub-second rather than the library
  default of 5s. It is a synchronous client called from async handlers, so a
  blocked lookup stalls the event loop for its full duration — five seconds of
  that is far worse than the assembly the cache exists to avoid.

## [0.10.4] - 2026-07-27

### Added

- **The documentation site is actually served**, at `/docs` on the app's own
  origin, with a nav link and a route back to the app from every page. It had
  been built and gated but never deployed: `/docs` returned HTTP 200 only
  because the SPA catch-all answers every unknown path, so nothing looked wrong.
- **Search the network by name.** The site's primary call to action is "find your
  workshop", and among ~3,200 spaces there was no way to type a name. Matches on
  name, city, and country, ignoring accents, punctuation, and word order.
- **Near-miss tolerance on match results.** A slider measured in *missing
  requirements* rather than a percentage, bounded by the design's size
  (`max(r-2, 0)`, defaulting to one gap) — one gap means something different in
  a design with two requirements than in one with six.
- **Guided form for "New design".** It previously accepted only pasted JSON,
  which asks the author to already know the OKH format. It now opens the same
  tiered editor the URL import uses; pasting JSON remains one click away.
- **Contact page**, at contact@openhardwaremanager.org.
- **`vinyl_cutting`** process. Maps of Making publishes a `vinyl-cutting`
  activity OHM had no process for, so those spaces' capability was dropped on
  ingest.
- **Taxonomy drift gate.** `PROCESS_DEFINITIONS` is generated from
  `processes.yaml`, with `--check` as `make ready` step 8/11. The two were
  hand-synchronised across 49 processes with nothing asserting they agreed.
- **The frontend gate now runs in CI** — typecheck, lint, unit, build, and the
  Playwright/a11y suite. It had no CI coverage at all.

### Changed

- **Cloning is the default extraction path** for generate-from-URL, with
  automatic fallback to the platform API if a clone fails. A public clone needs
  no credential, so self-hosted instances work out of the box and the hosted
  instance no longer subsidises every user's extraction through one shared,
  rate-limited token. Measured on `RespiraWorks/Ventilator`: API path 504 after
  120s, repeatedly; clone path 200 in ~21s.
- **Match results lead with coverage, not a score.** "Missing 1 of 4
  requirements" or "Meets every requirement", with confidence demoted to a
  secondary line.
- **Deploys pin image digests** instead of a mutable tag, and assert build
  identity afterwards — images now carry `GIT_SHA`, reported at `/health` as
  `build` and served at `/build-info.json`.

### Fixed

- **Deploys were silently doing nothing.** Publishing 0.10.3 overwrote the
  release tag with a new digest, then the deploy set the same image reference
  already running — so Container Apps created no revision and the previous image
  kept serving, while both deploy jobs reported success. Every check tested
  liveness rather than identity, and the stale image reported the same version.
- **Full country names everywhere.** Filters mixed "France" with "BJ": name
  resolution used a hand-maintained table of ~46 countries against a network
  holding 140 distinct values, 96 of them codes. Now resolved via
  `Intl.DisplayNames` — verified against all 96 codes in production. A code and
  its full name also no longer appear as two separate filter options.
- **Generation timeouts no longer report themselves as user cancellations**,
  which left no clue whether to retry, wait, or give up.
- **Accessibility:** 19 serious contrast violations in the tiered editor, and a
  pre-existing one in the design picker's selected row. The a11y helper also
  scanned mid-animation, producing intermittent failures against colours that
  exist in no stylesheet; it now waits for animations to settle.

## [0.10.3] - 2026-07-26

### Added

- **Public documentation site (`docs-site/`):** a human-facing site for
  openhardwaremanager.org, separate from the developer corpus in `docs/`.
  Fourteen pages — narrative (`about/`), task guides (`guides/`), and reference
  including a "what's built" page generated from the codebase.
- **Docs status gate:** `tests/parity/test_docs_status.py` (R1–R9) as `make ready`
  step 7/10, plus `make docs-site` and `make docs-status`. Coupling is structural
  by directory, so a guide cannot claim a capability the frontend does not expose;
  `SiteDoc.requires_fe_call` checks that at capability granularity.
- **Generate a design from a repository URL (web UI):** point OHM at a public
  GitHub or GitLab repository, review the extraction through a guided tiered
  editor (required fields save-gated, matching drivers next, long tail collapsed),
  and download as **YAML or JSON** — or hand the reviewed manifest straight to
  matching without saving it. Wires up `POST /api/okh/generate-from-url`, which
  previously had no frontend caller.
- **Optional manual Azure deploy:** the release workflow takes a `deploy` input
  (default false), so a manual run can publish an image without shipping it, or
  deploy without waiting for a version tag.

### Changed

- **`LayerConfig.use_nlp` now governs all spaCy usage in generation**, not just
  the NLP layer. BOM collection reached for spaCy independently, so disabling NLP
  did not disable NLP. Note it is no longer a performance lever — with the misuse
  below fixed, the regex fallback costs about the same.
- **MkDocs pinned `<2`** with `mkdocs-material>=9.7,<10`; both were unpinned, so a
  routine sync could have pulled MkDocs 2.0 (no plugin system, TOML config, no
  stated licence). Removed the unused `mkdocs-mermaid2-plugin`.

### Fixed

- **Generation is ~7× faster.** Two misuses of spaCy in BOM collection: a
  full-document parse whose result was never read, and the full neural pipeline
  run 2,117 times to perform a word-membership test that needed only tokens.
  Measured on `RespiraWorks/Ventilator`: **120.5s → 17.0s wall, 112.4s → 16.3s
  CPU**, with byte-identical output. Repositories that previously exceeded the
  proxy timeout and failed now complete.
- **`git` installed in the runtime image**, so the generation clone path
  (`clone=true`) works. It failed instantly in production every time, silently
  forcing all generation onto the slower per-file API path.
- **The port check in `scripts/validate_docs.py` was dead code** — its regex only
  matched a form `src/config/settings.py` had not used for some time, so it
  silently validated nothing. Now live, and covering both documentation corpora.
- **Frontend unit test expectation** for `deriveFilterOptions`, which still
  expected ISO country codes after 0.10.2 changed them to display names.

### Security

- **`gitpython>=3.1.55`** (resolves to 3.1.57) for GHSA-fjr4-x663-mwxc,
  GHSA-6p8h-3wgx-97gf, GHSA-r9mr-m37c-5fr3, and GHSA-94p4-4cq8-9g67.

## [0.10.2] - 2026-07-23

### Added

- **Process inference service:** modular file-type + title/keyword →
  `manufacturing_processes` (`ProcessInferenceService`), wired into OKH
  generation and `ohm okh infer-processes` backfill (dry-run / `--apply`).
- **Remote file type resolution:** extensionless downloads (e.g. Thingiverse)
  resolve via redirect/Content-Disposition so the UI shows STL Mesh etc.
  instead of Unknown.

### Changed

- **Facility country display:** network spaces and UI normalize ISO codes to
  full names (`FR` → `France`); filters treat code and name as equivalent.

### Fixed

- Sparse Match UI when stored OKHs had empty `manufacturing_processes` despite
  design files / `3DP-…` titles — backfill path and generation safety net.

## [0.10.1] - 2026-07-21

### Fixed

- **OKH create/upload 500:** `POST /api/okh/create` and `/upload` persisted the
  manifest then failed building `OKHResponse` (missing SuccessResponse
  `message`/`status`). Responses now use the same construction as GET-by-id
  (201 with `success` + `okh`). Contract test:
  `tests/api/test_okh_create_response.py`.

## [0.10.0] - 2026-07-21

### Added

- **Federated identity (backend slices 0–8):** accounts and API keys with write enforcement; offline capability grants (`did:key`); custodial identity mint/rotate; record provenance store + federation propagation; per-record visibility; space claims and edge bootstrap; certification attestations (R3 bundle hash); domain/OAuth bindings and trust-on-follow directory; peacetime / crisis / shielded security-mode presets. CLI and API under `ohm identity` / `/v1/api/identity/*`.
- **Frontend Track F (F0–F6):** session auth (Bearer key in `sessionStorage`); admin Settings (Session, Keys & accounts, Identities, Grants, Spaces, Bindings, Directory, Federation, Reputation); Packages as first-class nav (list/search, server build, zip download); OKH/OKW create with provenance and visibility controls; attestations/certify on package detail.
- **Package batch zip:** `POST /api/package/download-zip` and CLI `ohm package download-zip` for multi-package download.
- **Authentication & IAM docs:** new MkDocs section (`docs/auth/`) covering bootstrap `API_KEYS`, accounts vs keys, DID minting, and the Settings UI; cross-links from API auth and identity-model docs.

### Changed

- **Version:** Application release `0.10.0`. Published Docker tags will include `0.10.0`, floating `0.10`, and `latest`.
- **Settings IA:** Session/Connect is reachable without admin so operators can paste the first env key; admin tabs appear after `whoami` reports `admin`.

### Fixed

- **Session chicken-and-egg:** Settings was admin-gated, which hid the only UI path to paste a bootstrap API key; Connect/Session is now always available.
- **Package build 500:** successful `POST /api/package/build/{manifest_id}` returned a `SuccessResponse` model where FastAPI expected a dict; response is now serialized correctly (201 with metadata).

## [0.9.0] - 2026-07-12

### Added

- **OKH Materials quality pipeline:** stronger Materials extraction and post-processing (`materials_filter`, confidence scoring, optional LLM triage, review helpers) so generated manifests drop prose/table noise and near-duplicate line items more reliably.
- **Materials quality harness + Azure regen tooling:** baseline metrics, fixture set, and batch canary hardening (progress heartbeats, per-repo timeouts, incremental reports); `okh_generation_materials_regen_compare.py` for before/after scoring; `okh_generation_azure_regen_batches.py` for resumable production-container re-generation with BOM sidecars and a JSONL process log.
- **OKH-LOSH v2.4 TOML import:** `OkhLoshConverter` converts OKH-LOSH v2.4 TOML manifests (github.com/iop-alliance/OpenKnowHow) to OHM's canonical OKH manifest, with kebab→snake field mapping and unmapped fields preserved under `metadata.*`; `ohm convert from-okh-losh`; `POST /v1/api/convert/from-okh-losh`; docs at `docs/conversion/okh-losh-toml.md`; bulk-import driver at `scripts/import_okh_losh_batch.py`.
- **Designs catalog browse UX:** catalog/list view toggle, alphabetical/category sort, group-by (category / process / license / none), friendlier display titles, richer cards (category, processes, author, version, license), and consolidated license facets (e.g. CERN-OHL / AGPL variants collapsed).
- **Match workflow UX:** searchable `DesignPicker` with filters; facility filters expanded with city / state-region / country; network (incl. Maps of Making) facilities available as match candidates; multi-select match solutions with per-solution supply-tree links and RFQ handoff; facility detail hands off to Match with the facility preselected.
- **Frontend query cache:** React Query persists low-volatility catalog/network data to `localStorage` (1-hour TTL), shares the `["network","baseline"]` key across Home / Network / Match, and exposes a NavBar **Refresh data** control.

### Changed

- **spaCy model:** NLP matcher / loader defaults to the medium (`md`) model instead of small (`sm`) for better matching quality.
- **Version:** Application release `0.9.0`. Published Docker tags will include `0.9.0`, floating `0.9`, and `latest`.

### Fixed

- **Test isolation from live Azure:** root and integration conftests force `STORAGE_PROVIDER=local` before app import (winning the race against import-time `load_dotenv()`), clear service singletons in the integration client fixture, and extend the outbound-network guard to the integration lane so `.env` azure_blob settings can no longer hang `make ready`.
- **Match a11y + e2e:** `DesignPicker` listbox markup satisfies ARIA required-children/parent rules; facility-detail e2e updated for the Match handoff CTA.

## [0.8.11] - 2026-07-10

### Added

- **File type taxonomy:** canonical YAML taxonomy (`src/config/taxonomy/file_types.yaml`) with technical type, OKH role, and render tier (`native_inline`, `text_viewer`, `wasm_3d`, `download_only`); `GET /v1/api/file-types` and `ohm file-types list|validate`; ADR at `docs/architecture/file-type-taxonomy-adr.md`.
- **OKH file browsing UX:** path-normalized `display_path` / directory grouping in a nested tree (root-first); inline preview panel for images, PDF, and markdown/text; full-page preview at `/okh/:id/files/*`; download for CAD/mesh and other non-previewable types. Detail responses enrich file refs with `display_path`, `directory`, `file_type`, `render_tier`, and `mime_type`.
- **Local Build Package:** OKH detail (and RFQ) **Build Package** writes a package folder on the user's machine via the directory picker (Chrome/Edge), with write-access probe and per-file graceful failures; Firefox/Safari fall back to a browser-built `.zip`.

### Changed

- **OKH detail layout:** Intended Use section moved above Files & Documentation.

## [0.8.10] - 2026-07-08

### Added

- **OKH manifest file proxy (#272):** `GET /v1/api/okh/{id}/files/{path}` streams design and manufacturing files from blob storage or the manifest `repo` URL; OKH detail enriches file refs with `url`; frontend uses proxied links; `ohm okh download-file`; `probe_okh_files` prefers `url` / `download_url`.

### Fixed

- **ACA production stability:** Gunicorn defaults to 1 worker and 300s timeout in `production.toml` (prevents OOM crash loop on 1 vCPU with eager NLP init).
- **Frontend ACA deploy:** fractional CPU values (e.g. 0.5) accepted for the nginx sidecar.
- **Release workflow:** deploy verify retries with clearer logging against `/health/liveness`.

## [0.8.9] - 2026-07-08

### Added

- **Unified distributed cache (#271):** pluggable `CacheBackend` with `memory` (default) and `redis` backends; shared by `@cache_response` and `cached()`; cache stats on `GET /v1/api/utility/metrics`. Optional Redis service in `docker compose --profile redis`.
- **ACA triage harness and production probes:** `make harness` / `make harness-probes` with `probe_match`, `probe_cache`, `probe_okh_files`, and `probe_latency`; proposal workflow under `docs/testing/probe-workflow.md`.

### Fixed

- **Match 503 cold start on ACA (#270):** `MATCHING_EAGER_INIT` pre-loads `MatchingService` during app lifespan; `/health/readiness` reports `matching_service`; frontend surfaces API `request_id` on match errors.
- **Release workflow:** backend deploy verify tolerates ACA cold-start; frontend publish waits on backend tests; changelog gate for tagged releases.

## [0.8.8] - 2026-07-07

### Changed

- **`OKW_SOURCE` unset now defaults to `union` (storage ∪ Maps of Making), not storage.** A match with no configured source is no longer silently limited to blob storage — it draws candidates from both the configured storage backend and the MoM network. `OKW_SOURCE=storage` restricts to blob only and `OKW_SOURCE=mom` to MoM only; `MATCHING_LOCAL_OKW_JSON_DIR` still yields a storage-only local pool (never unioned). Precedence: the environment sets the candidate universe and a per-request override may narrow within it but never broaden it. `okw_source_resolved` now distinguishes unset (→ union) from an explicit `storage`.
- **One shared facility-pool resolver for API and CLI.** `POST /v1/api/match` and the `ohm match` CLI now resolve the candidate pool through a single `OKWService.resolve_match_facilities` (structural parity, not copy-paste), which routes every source through the network surface (`get_network_match_facilities`). MoM candidate loading degrades gracefully — when MoM is unavailable, `union` still returns the storage pool. Facilities without map coordinates are retained for matching (they are only dropped from the map/browse surface).

## [0.8.7] - 2026-07-06

### Added

- **Typed configuration schema + per-environment files (config Slice 1):** a `pydantic-settings` schema (`src/config/schema.py`) is now the single source of truth for the storage target (provider / account / container), the runtime `environment`, `OKW_SOURCE`, and CORS. Non-secret values are checked in per environment at `config/environments/{development,test,production}.toml` and layered under process env vars (env wins); secrets (`AZURE_STORAGE_KEY`, `API_KEYS`, `LLM_*`) stay env/`secretRef`-only. `settings.py` and `storage_config.py` consumers read the schema; the old inline env-read paths were removed. Behaviour-preserving — the `docker --env-file` quote-stripping quirk is consolidated into one normalizing env source, and characterization tests pin per-setting equivalence.
- **Generated `env.template` + staleness gate:** `scripts/generate_env_template.py` emits the schema-owned settings into a marked block of `env.template` (name, default, secret-vs-not). `make env-template` regenerates it (part of `make format`), and a CI step + unit test fail if the committed block drifts from the schema — the lockfile pattern already used for the repository map.
- **Config drift guards (startup posture + `/health` fingerprint + deploy gate):** the app now validates its config at startup — hard-failing in `production` on invalid/missing storage config, warning and degrading elsewhere. Public `/health` gains a best-effort, time-boxed `storage` fingerprint (resolved provider / account / container + `okh/`/`okw/` object counts) so config/data drift is visible. The release workflow's post-deploy step asserts the live container matches `config/environments/production.toml` and that counts are non-zero — an empty or mis-pointed prod container fails the deploy (this is exactly the drift that caused the live zero-match).

### Changed

- **Deploy pipeline now applies the non-secret storage target from the repo.** `deploy/scripts/deploy_azure.py` previously only set `ENVIRONMENT` + `CORS_ORIGINS` and left `STORAGE_*` configured directly on the container app (invisible to the repo — the drift that caused live zero-match). It now authoritatively applies every non-secret value from `config/environments/<environment>.toml` (incl. `AZURE_STORAGE_CONTAINER`) via additive `--set-env-vars`. Secrets are refused by `deploy_env_vars()` and existing `secretRef`s (e.g. `AZURE_STORAGE_KEY`) are left untouched.

## [0.8.6] - 2026-06-30

### Fixed

- **MoM `OKW_SOURCE=mom` silently overridden by `MATCHING_LOCAL_OKW_JSON_DIR`:** `POST /v1/api/match` checked the local-dev JSON directory override before `OKW_SOURCE`, so an explicit request to use the Maps of Making SPARQL bridge as the facility source was silently ignored whenever that dev-convenience env var was set — a divergence from the CLI's `--okw-source mom`, which always reached MoM. `OKW_SOURCE` is now checked first in `_get_filtered_facilities`.
- **CORS preflight 400 on deployed containers:** `CORS_ORIGINS` defaults to an empty list (deny all) in production when unset, which makes Starlette's `CORSMiddleware` reject every browser CORS preflight with 400 before the request reaches a route handler. None of the GCP/AWS/Azure deployment config paths (`deployment.yaml` via `from_dict()`, or the `deploy_gcp.py` CLI script via `with_defaults()`) ever set it. All deployment config construction paths now default `CORS_ORIGINS` to `"*"` (supply-graph-ai is a public API) unless explicitly overridden.

### Added

- **MoM integration documentation and test coverage:** `docs/runbooks/mom-integration-e2e-validation.md` — CLI/API demo runbook verified against the live MoM SPARQL endpoint, plus unit tests for `mom_bridge.py`, taxonomy `wikidata_qid` lookups, and `OKW_SOURCE` routing (none existed since the integration shipped in `#181`).

[0.10.1]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.10.0...v0.10.1
[0.10.0]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.11...v0.9.0
[0.8.11]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.10...v0.8.11
[0.8.10]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.9...v0.8.10
[0.8.9]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.8...v0.8.9
[0.8.8]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.7...v0.8.8
[0.8.7]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.6...v0.8.7
[0.8.6]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.5...v0.8.6

## [0.8.5] - 2026-06-29

### Fixed

- **`GET /v1/api/okh` timeout:** `SmartFileDiscovery.discover_files()` cascaded to full-bucket strategies (metadata scan, content-validation) when the `okh/` prefix listing returned an empty list, causing it to download every blob in the Azure container. The cascade now only advances when a strategy raises an exception (storage unavailable); an empty result is treated as authoritative and stops the search immediately. `_discover_by_directory_structure` re-raises storage exceptions so the caller can make the cascade decision correctly.

[0.8.5]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.4...v0.8.5

## [0.8.4] - 2026-06-25

### Added

- **Repair workflow epic (GAPs 1–8):** End-to-end API and CLI surface for field-device repair workflows — `AssetRecord` physical-state domain object, `AssetStatus` lifecycle field, repair document extraction pipeline, parts harvesting (`POST /v1/api/asset/harvest-parts`), triage checklist (`POST /v1/api/asset/triage-checklist`), triage report with per-component action recommendations, salvage matching (fleet query for harvestable components), sourcing resolution (`POST /v1/api/asset/resolve-sourcing`), repair-doc import with conservative merge semantics (GAP-4), cross-manifest compatibility via `compatible_manifest_ids` (GAP-8), and claim/reservation mechanism for harvestable components (GAP-7).
- **`make ready` gate:** Single command (`make ready`) that enforces format, lint, unit tests, service↔API↔CLI parity, docs validation, and live E2E as a pre-merge gate. Individual targets: `make parity`, `make validate-docs`, `make e2e`.

### Fixed

- **Azure Container Apps redirect scheme:** Gunicorn was not configured to trust `X-Forwarded-Proto` from ACA's TLS-terminating ingress, causing all trailing-slash redirects to generate `http://` URLs instead of `https://`. Added `forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")` to `gunicorn.conf.py`.
- **`make ready` / parity gate:** Wired `validate-docs`, `parity`, and `e2e` targets into the project Makefile; `make parity` runs `tests/parity` to catch service↔route↔CLI drift early.

[0.8.4]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.3...v0.8.4

## [0.8.3] - 2026-06-20

### Added

- **OKH field presence and completeness metadata** (`#171`): validation output now includes a per-field coverage report.
- **Geographic facility filtering** (`#172`): OKW search accepts `country`, `region`, and `city` query parameters.
- **`Component` data model** (`#173`): structured sub-component references inside OKH manifests.
- **User-driven version pinning** (`#174`): `POST /v1/api/package/pin` locks a package to a specific OKH version.
- **Cryptographic package signing** (`#175`): packages can be signed via federation identity; signature verified on import.
- **OKH bulk import/export** (`#176`): `POST /v1/api/okh/import-collection` and `GET /v1/api/okh/export-collection` for manual collection sync.
- **Setup skill:** `.claude/skills/setup/SKILL.md` — natural-language onboarding wizard for OHM configuration.

[0.8.3]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.2...v0.8.3

## [0.8.2] - 2026-06-04

### Fixed

- **Docker `--env-file` breaks remote storage (quoted env values):** `docker run --env-file` passes values verbatim including surrounding quotes, while `docker-compose` / `python-dotenv` strips them. The `_env()` helper in `storage_config.py` now defensively strips `"` and `'` from all credential and bucket-name variables, preventing DNS failures such as `Cannot connect to host '"myaccount"'.blob.core.windows.net`.
- **Azure Key Vault init noise on every command:** The secrets manager incorrectly detected an Azure Key Vault environment whenever `AZURE_STORAGE_ACCOUNT` was present in `.env`, triggering a noisy warning about missing optional packages on every CLI invocation. Detection now requires `AZURE_KEY_VAULT_URL` or `WEBSITE_INSTANCE_ID` to be set.
- **Blank `"Unexpected error: "` message:** `APIClient.request()`'s catch-all exception handler now always includes the exception type in the message (`Unexpected error (ExcType): detail`), so errors can never silently produce an empty description.

### Documentation

- `README.md` and `docs/development/container-guide.md` updated with explicit `docker run --env-file` guidance, per-provider env-var tables, and a troubleshooting section on the quoted-value DNS failure.

[0.8.2]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.1...v0.8.2

## [0.8.1] - 2026-06-04

### Fixed

- **OKH parser:** `OKHManifest.from_dict` now accepts plain strings in `making_instructions`, `design_files`, `manufacturing_files`, `operating_instructions`, `technical_specifications`, and `publications` — converting them to `DocumentRef` objects with a field-appropriate `DocumentationType`. Previously, string items crashed with `AttributeError: 'str' object has no attribute 'get'`, producing an opaque error in both `ohm okh validate` and `ohm okh fix`.
- **OKH parser:** `standards_used` now accepts plain strings (e.g. `"CC0-1.0"`) in addition to dicts, coercing them to `Standard(standard_title=<string>)`.
- **Codebase:** Removed ~100 redundant inline section comments (`# Required fields first`, `# Optional fields after`, etc.) from API model files; moved module-level imports that were deferred inside methods; simplified `validate_input` in `MatchRequest` from 9 repeated `if x is not None` branches to two list comprehensions; removed dead conditional in `cleanup_service._detect_broken_links` where both branches were identical; removed commented-out dead code from `settings.py`.

### Added

- **Characterization tests:** 138 new unit tests covering `CapabilityRule`, `CapabilityRuleSet`, `CapabilityRuleManager`, `CapabilityMatcher`, `BaseMatchingLayer` utilities, `DirectMatcher`, and `HeuristicMatcher` — raising coverage on those modules from 10–42% to 78–96%.

[0.8.1]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.0...v0.8.1

## [0.8.0] - 2026-06-04

### Added

- **Federation MVP (opt-in):** LAN peer catalog sync via HTTP (`/v1/api/federation/*`), mDNS discovery, follow allowlist, and anti-entropy Merkle sync. Disabled by default (`OHM_FEDERATION_ENABLED=false`). See [federation MVP ADR](docs/architecture/federation-mvp-adr.md).
- **Release automation:** GitHub Actions `Release` workflow validates git tags against `pyproject.toml`, runs pre-release tests, and publishes Docker images to Docker Hub.
- **Release tooling:** `scripts/bump_version.py`, `scripts/validate_release_version.py`.
- **Test harness:** Path-based pytest lane markers in `tests/conftest.py`; contract stability guardrail suite.

### Changed

- **Version:** Application release `0.8.0` (pre-1.0 stable). Single runtime version via `get_version()` / `pyproject.toml`.
- **Docker image:** Built from frozen `uv.lock` (aligned with CI). Published as `touchthesun/openhardwaremanager` with tags `0.8.0`, `0.8`, and `latest`. Multi-arch manifest (`linux/amd64`, `linux/arm64`) via `docker buildx`.
- **Dependencies:** Security-pinned transitive deps (FastAPI ≥0.120, Starlette, urllib3, idna, gitpython, aiohttp); `pip-audit` in CI and release workflows.
- **CI:** Docker build-test on `main` push; `develop` branch name fixed to `dev`; GitHub Actions upgraded to Node.js 24–compatible action majors.

### Fixed

- Contract test lane no longer runs live package-download integration tests (requires `RUN_LIVE_API_TESTS=1`).
- Package download route tests no longer stub `matching` in a way that breaks other unit tests.

[0.8.0]: https://github.com/helpfulengineering/supply-graph-ai/releases/tag/v0.8.0
