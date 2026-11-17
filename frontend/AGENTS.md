<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# Orientation

Added below the generated block on purpose: `next dev` rewrites only the
region between its own markers, so this survives.

**The App Router is `frontend/app/`, not `src/app`.** `src/` holds everything
else — `features/` (view-level components, one directory per surface),
`components/` (shared UI and layout), `api/ohm/` (typed clients), `context/`,
`views/` (page-level compositions the route files render), `lib/`. A route file
under `app/` is usually four lines that render a view.

`app/error.tsx` and `app/global-error.tsx` already exist and are well built. In
this version of Next the error boundary prop is `retry`, not `reset`.

**Types are generated from the live API.** `src/api/generated/schema.d.ts` comes
from `npm run gen:api`, which boots the backend and dumps its OpenAPI. Run it
after any backend route or response-model change, and commit the result — the
parity suite compares it against the running app and fails on drift.

The list endpoints type their items loosely (`items: object[]` in OpenAPI), so
the clients in `src/api/ohm/` narrow them by hand. When a list carries a field
the detail type does not — `visibility` is the current example — express that as
a distinct list-item type rather than widening the shared model.

**The gate is `npm run frontend-ready`** from this directory: typecheck, lint,
unit, build, then Playwright e2e including an a11y pass and a responsive lane at
two widths. A new top-level route should be added to the responsive lane's
route list and declared in `tests/parity/manifest.py` under the owning area's
`fe_routes`.

**Session storage, not local.** The API bearer token lives in `sessionStorage`
under `ohm_api_key`. Tests assert it never reaches `localStorage` — which the
app does use, for theme and domain preference, so assert on the credential
rather than on the store being empty.

## Membership UAT (`e2e/uat/`)

The weekly UAT lane encodes the intended operator and member workflows as one
ordered story (`@membership` parts 0–5 in a browser; `@federation` parts 6–10
over CLI/HTTP). It is not a pixel freeze and it is not a second product. When
the product's intended use cases change, this suite has to change with them —
otherwise it either blocks a deliberate UX shift or silently certifies an
outdated path.

Treat updates with nuance:

- **Same change when the story moves.** If you change a flow the UAT names —
  registration modes, invite links, Settings tabs a coordinator sees, On
  behalf of / attribute, curated lists — update the matching `e2e/uat/`
  step (and its Pass-line `test.step` wording) in the same change. Leaving
  the suite green against the old wording is a regression of the runbook,
  not a pass.
- **Do not overfit to incidental chrome.** Assert the outcome the person was
  proving (signed in as X, form absent, facility listed without the street,
  organisation on Authorship). Prefer roles and accessible names. A
  restyle, reorder of optional fields, or copy tweak that does not change
  the workflow is not a reason to rewrite the part.
- **Product change vs suite rot.** A failing UAT after an intentional UX
  change is a prompt to revise the story, not to weaken the assertion or
  skip the lane. A failing UAT after an unrelated change often means a
  shared control (Session paste, Register form, Settings nav) shifted —
  fix the helper once rather than patching every part.
- **Throwaway nodes only.** The suite creates and deletes accounts. It
  refuses to start unless `UAT_THROWAWAY_NODE=1`. Never point it at a stack
  whose `.env` names real storage. Details: `harness/README.md` and
  `.github/workflows/uat-e2e.yml`.
