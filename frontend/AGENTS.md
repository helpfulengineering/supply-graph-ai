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
