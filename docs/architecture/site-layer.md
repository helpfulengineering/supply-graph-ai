# The optional site layer

OHM is software you run yourself. The hosted instance is a convenience, not the
product — so the whole *site* layer is a capability each instance opts into,
and it defaults to **off**.

This follows the same idiom as [`OHM_SECURITY_MODE`](security-modes.md): a
posture selected by environment variable, read through config, never
hard-coded.

## Status: conditional keep, review by 2027-02-28

No environment enables this layer. `config/environments/*.toml` does not mention
Supabase, no deploy step sets the two `NEXT_PUBLIC_OHM_SUPABASE_*` variables,
and no project is provisioned — so on every deployment that exists today, this
is code that does not run.

It is kept anyway, deliberately, on measured grounds rather than optimism:

- **It costs nothing to carry.** The Supabase SDK is code-split into a chunk the
  initial document never references — verified against a production build, not
  assumed. `track()` returns immediately when the layer is off, `/operator-tools`
  is a real 404, and the whole suite is 93 unit tests adding ~3s.
- **It is finished, not a stub.** Both postures were verified against real
  builds when it was written, and CI now proves both on every run
  (`site-layer-enabled` in `ci-cd.yml`).
- **Cutting is a one-way door.** Roughly 3,900 lines with tests, plus a
  428-line schema. "We can add it back later" is not a thing anyone does.

**The condition.** This is a keep with an expiry, not a park. If the hosted
instance has not enabled the layer by **2027-02-28**, cut it — at that point the
"we might want it" argument has failed its own test, and what remains is code
that reads as live to every contributor who opens it while never having run.

Whoever cuts it: delete `src/features/site/`, `src/lib/site/`, `supabase/`,
`app/operator-tools/`, `e2e/site-layer.spec.ts`, the `site-layer-enabled` CI job
and this document, and drop `@supabase/supabase-js`. Three files outside the
layer then need an edit, and one needs a glance:

| File | What to remove |
|---|---|
| `src/features/match/MatchView.tsx` | the `track(EVENTS.matchRun, …)` call and both `lib/site` imports |
| `src/components/layout/NavDrawer.tsx` | `useSiteLayer()` and the `site.enabled &&` guard around the Operator group |
| `app/providers.tsx` | `siteConfig` (the `data-site-layer` attribute) and `<RouteTelemetry />` |
| `src/api/ohm/federation.ts` | a comment pointing at `lib/site/stack.ts` as prior art — prose, not a dependency |

Note the last one: `e2e/site-layer.spec.ts` and `app/providers.tsx` are a pair.
The spec reads the posture from the `data-site-layer` attribute that
`providers.tsx` publishes, so removing one without the other leaves a spec
asserting against an attribute nothing writes.

## Off is a first-class state

With no Supabase configured, an instance is **not degraded**. It is the default
deployment:

- theme and mode preferences live on the device
- there is no visitor gate
- no telemetry is collected or sent
- `/operator-tools` returns a real 404, and no nav entry advertises it
- the Supabase SDK is code-split into a lazy chunk the browser never fetches

"Configure Supabase" must never appear as an error or an empty panel. The
capability simply does not exist on that instance, and the UI reads as
intentional.

## What the gate gates

With the layer on, arriving at `/operator-tools` without a visitor record on
the device raises the sign-in gate. It stands in front of **that surface only**.

It never stands in front of the app. Browsing designs, matching against
facilities, and every write authorised by an OHM API key are untouched by it —
a telemetry sign-in that blocked them would be the site layer reaching across
the boundary below. `e2e/site-layer.spec.ts` asserts in *both* postures that no
dialog blocks the dashboard.

The gate is dismissible (Esc, the backdrop, "Not now"), and Operator Tools
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
| **Site layer** — visitor gate, telemetry, whitelabel, Operator Tools | Optional Supabase `ohmgr_*` | Who visited the **site**, and how it looks |

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
an operator on a fresh device goes straight to the token field. Operator Tools
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

## What is worth recording

Page views come from `RouteTelemetry`, mounted once above the routed subtree
and keyed on `usePathname`. They used to come from a mount effect in
`useSiteLayer`, which made the count a count of *that hook's mounts*: once per
hard load from the nav drawer, twice on the operator page, and never on a
client-side navigation. In a client-routed app that made `page` a landing-page
column wearing a page-view label.

Beyond page views the vocabulary is deliberately small, and the rule is that an
event must say something a path cannot. A design or facility being opened is
already a route, so a separate event for it would be the same fact twice. What
a path cannot express is an **outcome** — and `match_run` carries one, because
a match that finds no facility renders an ordinary page and is indistinguishable
from success in traffic. That is what makes "designs this network could not
make" computable, which is the one figure on the operator page that names an
action rather than describing the past.

`props` is the outcome half of an event and was write-only until it was added
to `ohmgr_admin_events`: `ohmgr_track` had always stored it and no read
function ever selected it. It stays out of the masked read.

**Nothing free-text ever goes in props** — no search queries, no form contents,
no names. Public catalogue ids and counts only. These rows are attributed to a
`visitor_email`, so a props blob carrying what someone typed would turn a usage
counter into a record of a named person's queries, which is a different product
with different obligations and one nobody opted into. `lib/site/events.ts`
states the rule where the events are named.

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
