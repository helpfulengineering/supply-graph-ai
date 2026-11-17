# Web UI verification harness

The single automated success signal for building this frontend — including
unattended, in a coding-agent loop. `make frontend-ready` (or
`npm run frontend-ready`) runs every check and exits nonzero on any failure.

## The gate (`frontend-ready`)

Runs in order, stops at the first failure:

1. **typecheck** — `tsc -b` (includes the generated API types, so backend
   contract drift is a compile error)
2. **lint** — `eslint .`
3. **unit** — `vitest run` (unit + component tests, jsdom)
4. **build** — `tsc -b && vite build`
5. **e2e (mocked) + a11y + screenshots** — `playwright test --project=mocked`

## E2E lanes

- **mocked** (default, in the gate): deterministic. API calls are intercepted
  with shared fixtures from `src/test/fixtures` — no backend required. Best for
  the autonomous loop and for portability.
- **real-api** (`npm run e2e:real`): no interception; hits the live OHM API via
  the dev-server proxy. Run on demand / in CI to validate real wiring.
- **uat** (`npm run e2e:uat -- --grep @membership` or `--grep @federation`):
  the membership runbook as one story told in order. `@membership` (parts 0–5)
  is a real browser against a real API; `@federation` (parts 6–10) is CLI and
  HTTP against the two-node stack and needs no page. Not in the gate and not
  part of `e2e` or `e2e:real`. Run weekly by
  [`.github/workflows/uat-e2e.yml`](../../.github/workflows/uat-e2e.yml), only
  when code has changed since the last run. See the rules below.

### The `uat` lane: throwaway nodes only

The suite creates and deletes accounts, mints keys and publishes designs. It
refuses to start unless `UAT_THROWAWAY_NODE=1` is set, because a maintainer's
`.env` often names a real storage container and the API on `localhost:8001` will
use it. Set the variable only for a node you started yourself with
`STORAGE_PROVIDER=local` and no cloud credentials. The workflow builds exactly
that node and sets it. Do not run the suite against the stack that `.env` in your
checkout describes.

What a run needs, besides the node: `API_KEYS` in the environment (the value the
node started with; the suite mints the operator with it), `API_UPSTREAM_URL` for
the frontend's `/v1` proxy, `UAT_API_URL` if the API is not on
`http://localhost:8001`, and the `ohm` CLI (`uv sync --extra dev` puts it in
`.venv/bin`; `UAT_OHM_BIN` overrides).

Things that differ from the other lanes, each on purpose:

- **Serial, no retries.** Parts build on each other, and a retry would re-run a
  step that has already changed the node and report a pass for a flow that did
  not work once. `workers=1` is in the npm script because Playwright cannot set
  it per project.
- **Screenshots are evidence, not baselines.** Nothing compares them to an
  earlier image. They are written to `artifacts/uat-evidence/`; the workflow
  keeps the last three runs and a `prune` job deletes the rest. A freshly shown
  one-time secret is masked in them.
- **People are browser contexts.** A token goes in through Settings → Session,
  the page a person would use, never by writing to storage.
- **The `ohm` helper treats empty output as failure.** The identity commands
  exit 0 and print nothing on a 401.
- **State lives in `artifacts/uat-world/world.json`,** not in module state, so a
  part that runs in a fresh worker after a failure finds what the earlier parts
  made, or says which part to run first. It holds tokens and is not uploaded.
- **Traces and video are kept on failure,** and a trace records request headers.
  That is acceptable because the node and its keys are destroyed when the run
  ends; it would not be on a node you intend to keep.

## Typed API client

`npm run gen:api` regenerates `src/api/generated/schema.d.ts` from the backend
OpenAPI spec (`openapiUrl` in `harness.config.json`). The generated types are
committed so the gate can typecheck without the API running; regenerate when the
backend contract changes and let `tsc` surface the breakage.

## Reusability seam

This directory (`harness/`) plus the test configs are **generic core** — no
OHM-specific values. Everything project-specific lives in
[`../harness.config.json`](../harness.config.json):

| Key | Meaning |
|-----|---------|
| `appStartCommand` / `appUrl` | how Playwright boots and reaches the app. Point it at a **production start**, not a dev server: lazy per-route compilation under parallel workers times out unrelated specs. The gate builds immediately before it runs. |
| `apiBaseUrl` / `apiHealthUrl` / `apiPathPrefix` | backend location + API path prefix |
| `openapiUrl` / `apiTypesOutput` | OpenAPI spec source + generated-types path |
| `routesToScreenshot` | routes captured for async visual review |

To reuse on another project: copy `harness/`, the test configs, and the test
scaffolding, then fill in a new `harness.config.json`. (A `scaffold-web-ui-harness`
skill to automate this is a planned follow-up.)

## Loop conventions (for the coding agent)

- Implement a slice → run `make frontend-ready`.
- **Green** → open a PR into the `frontend-dev` integration branch.
- **Red** → iterate up to a bounded number of attempts; if still red, open a
  **draft** PR with a STUCK report (what was tried, the leading hypothesis, and
  the single blocking question), then move to the next slice. Never merge; never
  thrash silently.
