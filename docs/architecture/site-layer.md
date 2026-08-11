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

## Two doors, not a ladder

Within the site layer there are two tiers, and neither leads to the other:

| Tier | Established by | Reads |
|---|---|---|
| **Visitor** | a name and email typed at the gate, verified by nobody | their own row in full; everyone else masked to `f***@d***` |
| **Operator** | the token from `ohmgr_admin_secrets`, hashed and checked server-side | everything unmasked, and every mutation |

Signing in never promotes you, and unlocking never requires a visitor record —
an operator on a fresh device goes straight to the token field. Mission Control
therefore offers that field at every tier rather than nesting it inside the
signed-in branch.

**`isOperator` is established by presenting the token, not by reading
`is_admin`.** The column is a display marker; the schema says so, and it has to
be, because the email a visitor claims at the gate is unauthenticated. Deriving
access from it would mean knowing an operator's address was enough to have
their access. So the check is a round trip: the held token goes to a
token-gated RPC, and the server's willingness to answer *is* the answer. This
is the same reasoning that keeps `isOperator` out of `isAdmin`, applied one
level down.

The client never decides what it may see. Each surface has two backing
functions — a masked one any signed-in visitor may call and an unmasked
operator one — and the masked variants do not return the withheld columns at
all. A frontend bug cannot leak an address the function did not send, and the
rendered rows carry which variant produced them, so an operator control cannot
be drawn over self-service data.

None of it is cached. The app persists its other queries to storage so a reload
starts warm; these panels opt out, because visitor names, addresses, and page
histories at rest on the device would undo the tier that gated them. The token
lives in `sessionStorage` for one tab and is verified before it is stored.

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

## Verifying both directions

The suite is expected to pass with the layer **off** (the default) and **on**.
`e2e/site-layer.spec.ts` covers the off direction on every CI run: no nav
entry, a 404 for the route, no site-layer console errors, and theme/mode still
working with no backend at all.
