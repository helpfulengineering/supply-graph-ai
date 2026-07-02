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
| `appStartCommand` / `appUrl` | how Playwright boots and reaches the app |
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
