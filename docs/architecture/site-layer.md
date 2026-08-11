# The optional site layer

OHM is software you run yourself. The hosted instance is a convenience, not the
product — so the whole *site* layer is a capability each instance opts into,
and it defaults to **off**.

This follows the same idiom as [`OHM_SECURITY_MODE`](security-modes.md): a
posture selected by environment variable, read through config, never
hard-coded.

## Off is a first-class state

With no Supabase configured, an instance is **not degraded**. It is the default
deployment:

- theme and mode preferences live on the device
- there is no visitor gate
- no telemetry is collected or sent
- `/mission-control` returns a real 404, and no nav entry advertises it
- the Supabase SDK is code-split into a lazy chunk the browser never fetches

"Configure Supabase" must never appear as an error or an empty panel. The
capability simply does not exist on that instance, and the UI reads as
intentional.

## What the gate gates

With the layer on, arriving at `/mission-control` without a visitor record on
the device raises the sign-in gate. It stands in front of **that surface only**.

It never stands in front of the app. Browsing designs, matching against
facilities, and every write authorised by an OHM API key are untouched by it —
a telemetry sign-in that blocked them would be the site layer reaching across
the boundary below. `e2e/site-layer.spec.ts` asserts in *both* postures that no
dialog blocks the dashboard.

The gate is dismissible (Esc, the backdrop, "Not now"), and Mission Control
keeps a sign-in button afterwards, so dismissal costs a visitor only the parts
that are genuinely per-person — their own record.

Its heading, body, and fine print are the operator's, read from the `gate` key
of `ohmgr_site_config`; empty strings mean "no preference" and fall back
field-by-field to the built-in copy. `{"enabled": false}` is how an operator
says this instance asks nobody to sign in. An unreachable or unprovisioned
config yields the default copy rather than an error — the gate still renders.

## Two vocabularies, deliberately named apart

This is the boundary the layer must not cross:

| Concern | Source of truth | Governs |
|---|---|---|
| **Application authorization** — API keys, DIDs, capability grants, `isAdmin`, `RequireAdmin`, the ten Settings panels | Backend `whoami` (unchanged) | What you may **do** in OHM |
| **Site layer** — visitor gate, telemetry, whitelabel, Mission Control | Optional Supabase `ohmgr_*` | Who visited the **site**, and how it looks |

Surfaced as **`isAdmin`** (application) and **`isOperator`** (site). Never
merged, never aliased.

This is not tidiness. OHM's [identity model](identity-model.md) promises
offline verification with no central authority; a second source of `isAdmin`
would make `RequireAdmin` and the Settings tab list obey two disagreeing
truths, and would put a network dependency inside an authorization path that
is specified to work without one.

## Enabling it

The operator runbook — every statement to run, and how to verify the boundary
holds — is
[Enable the site layer](../../docs-site/docs/guides/enable-the-site-layer.md).
In outline:

1. Create a Supabase project.
2. Run [`supabase/schema.sql`](../../supabase/schema.sql) in its SQL editor.
   It is idempotent and safe to re-run.
3. Set the operator token and grant `is_admin`, both from the SQL editor —
   neither is reachable from a client.
4. Set `NEXT_PUBLIC_OHM_SUPABASE_URL` and `NEXT_PUBLIC_OHM_SUPABASE_ANON_KEY`
   and rebuild. These are `NEXT_PUBLIC_` because the anon key is public by
   design: it can only call whitelisted `SECURITY DEFINER` RPCs.

The schema is prefixed `ohmgr_` rather than `ohm_` because the sibling
openhardwaremonitor project owns `ohm_` in the shared database.

## The telemetry wire contract

`ohmgr_track` takes `p_events`, an array of at most 25 objects. The **key names
are the RPC's, not the client's** — `supabase/schema.sql` reads each one with
`e->>'…'` and inserts it into the column of the same name, so a key the client
spells differently is not a rename, it is a `NULL` row:

| Wire key | Column | Source in `stack.ts` |
|---|---|---|
| `event` | `event` | the `track()` argument |
| `props` | `props` | the `track()` argument, capped at 2000 chars |
| `session_id` | `session_id` | `sessionId()` — per-tab, `sessionStorage` |
| `page` | `page` | `currentPath()` — `window.location.pathname` |
| `visitor_email` | `visitor_email` | `visitor()`, lowercased and trimmed |
| `ts` | *(none)* | sent for ordering; the column default `now()` wins |

Two of these carry consequences beyond display. `visitor_email` must be
lowercased and trimmed to match how `ohmgr_gate_signin` stores it, because
`ohmgr_delete_own` erases telemetry with `where visitor_email = e` — a row
written in another case is a row that "erase everything attributed to me"
silently misses. And every field is **omitted when empty** rather than sent as
`""`: `left('', 200)` stores an empty string, which the readers cannot tell from
a real value.

`buildTelemetryEvent` in `frontend/src/lib/site/stack.ts` is the single place
that builds this shape, and `stack.test.ts` pins the key names with a literal
assertion so a rename on either side fails loudly rather than quietly nulling a
column.

## Verifying both directions

`e2e/site-layer.spec.ts` covers the **off** direction on every CI run: no nav
entry, a 404 for the route, no site-layer console errors, and theme/mode still
working with no backend at all.

The **on** direction is covered at the unit level by `stack.test.ts`, which
builds an enabled client against a mocked Supabase endpoint and asserts both the
wire shape and the dormancy behaviour. It is **not** covered end-to-end: nothing
in CI sets `NEXT_PUBLIC_OHM_SUPABASE_URL`/`_ANON_KEY`, and because those are
inlined at build time an enabled lane needs its own build, not just its own
Playwright project. The branches in `site-layer.spec.ts` that test for the
enabled posture are therefore unreachable today.
