# UX Overhaul Playbook

A soup-to-nuts overhaul of OHM's frontend, carried out in seven pull requests:
migrate to Next.js, ship ten theme worlds in light and dark, consolidate every
route into a hamburger sitemap behind shared chrome, put the data surfaces on
tokens, and add an **entirely optional** site layer any instance can toggle.

The method came from a sibling project first. The expensive part was never the
CSS — it was learning the order to do things in, and which guarantees have to
exist *before* a repaint is safe. That order is what this document preserves,
now annotated with what actually happened when it met this codebase.

**OHM was already good, and this was additive.** Every phase extended a seam
the frontend already had.

---

## Part 1 — The worked example

The subject was
[binaryLady/openhardwaremonitor](https://github.com/binaryLady/openhardwaremonitor),
a fork of the dormant Open Hardware Monitor (C# / WinForms with a small
embedded HTTP server). It shipped a browser dashboard that had grown alongside
— but not into — the desktop application. Five pull requests took it from "a
static page bolted on" to a coherent product.

| PR | What landed |
|---|---|
| [#42](https://github.com/binaryLady/openhardwaremonitor/pull/42) | The dashboard became the UI the application itself serves, replacing a 2012 jQuery/Knockout bundle (~14.9k lines deleted). The embedded server learned directory routes, trailing-slash redirects, query-string handling, correct MIME types, a styled 404, and CORS. |
| [#43](https://github.com/binaryLady/openhardwaremonitor/pull/43) | The solution built again on current toolchains, CI compiled it on every push and published a runnable artifact, and a dependency-free Node agent brought the app to macOS and Linux. |
| [#44](https://github.com/binaryLady/openhardwaremonitor/pull/44) | Real sensors on macOS/Linux in **privilege tiers**, start-at-login, and the last hardcoded colour in the codebase replaced by a token read. |
| [#45](https://github.com/binaryLady/openhardwaremonitor/pull/45) | A live publishing endpoint, an install page, and honest copy. |
| [#46](https://github.com/binaryLady/openhardwaremonitor/pull/46) | Documentation trued up against shipped code, plus an upstream contribution package. |

### The six principles that did the work

**1. Tokens are the floor.** One token file is the only place a colour exists.
This is what makes ten worlds x light and dark cost about the same as one.

**2. The bench proves the palette, from live values.** Contrast is computed
from *runtime-resolved* token values, not numbers copied into a test. A palette
failing WCAG AA cannot ship, and adding a world automatically extends the
matrix.

**3. One component per concept; chrome is universal.** One header, one drawer
sitemap, one mode toggle, one footer — identical on every page, with a guard
enforcing it. Enforcing it is what keeps a design system from decaying into
suggestions.

**4. One data path, one failure path.** Demo data is a *source*, not a branch.
Every `if (demo)` you avoid is a divergence you never debug.

**5. Reuse and cite the existing architecture.** Re-implement behaviours with
citations of the code they mirror, and keep the wire contract byte-identical so
existing consumers never notice.

**6. Honesty over faking.** When you find overstated UX copy, prefer building
the thing it promised.

---

## Part 2 — What shipped, phase by phase

One pull request per phase, green before the next began.

### Phase 1 — Next.js foundation, zero feature change

Vite + `react-router-dom` v7 became the App Router on the **node runtime**. The
25-route tree moved to `app/` with pages delegating to the existing views;
router APIs ported mechanically across ~30 sites.

Three things did not port mechanically, and they are the interesting part:

- **`location.state` has no App Router equivalent**, and two flows depended on
  it (generate → match hands over a whole unsaved manifest; match → rfq carries
  selected solutions). `src/lib/navState.ts` stashes the payload under a nonce
  carried in the URL, sessionStorage-backed — which is *better* than what it
  replaced: it survives a refresh, which `location.state` never did.
- **nginx disappeared, so every guarantee it held needed a named owner**:
  `/v1/*` proxying, the `/docs` tree that must 404 rather than fall through
  (a 200 SPA shell once masked an undeployed docs site), `/healthz`,
  `build-info.json`, and fail-loud startup on an unset upstream.
- **`make parity` would have broken.** `tests/parity/inventory.py` read
  `App.tsx` with no existence guard and regex-scraped `<Route path>`; deleting
  that file raises `FileNotFoundError`, and `make ready` runs `make parity`. It
  now enumerates `app/**/page.tsx`, and `manifest.py` is unchanged — the same
  prefixes come out, which is the test.

**On "tests pass unmodified":** all 58 Playwright specs did, byte-for-byte,
because they are black-box. Six vitest component tests could not — they
imported `MemoryRouter`, which does not exist here — so their *harness* changed
while no assertion did. Stating that distinction honestly is part of the
method.

### Phase 2 — Token layer: ten worlds x light/dark

Colour lived in **1,425 hardcoded Tailwind utilities across 66 files**, while a
complete shadcn token seam sat unused. `src/styles/tokens.css` now carries
twenty palettes, generated from the reference rather than transcribed.

**The load-bearing decision is how mode is signalled.** The reference stamps two
attributes (`data-ttm-theme` x `data-ttm-mode`). OHM already had a mode
mechanism — the `.dark` class that `@custom-variant dark` binds every Tailwind
`dark:` utility to — and a second signal would leave those utilities and the
tokens disagreeing. So **mode stays `.dark`; only the world is an attribute.**

That makes specificity load-bearing:

- `.dark` alone is **(0,1,0)**
- a world block `:root[data-ttm-theme="x"]` is **(0,2,0)** — it *beats* `.dark`

So a world's light palette would win even in dark mode. Every world therefore
declares **both** polarities, the dark one at (0,3,0). Collapsing a world to a
single block reintroduces exactly that bug, which is why the file says so in
place: it looks like harmless duplication.

The shadcn bridge is **one block, not one per world**. Custom properties
resolve at use time, so changing `--ttm-surface` re-themes every component
reading `--card`. Twenty variants cost the same as one, and no shadcn primitive
was edited.

### Phase 3 — The contrast gate, before any repaint

`e2e/themes.spec.ts` scans every world x polarity — twenty variants — asserting
no serious or critical WCAG AA violations, reusing `expectNoA11yViolations`
verbatim. The matrix iterates `THEMES` from the hook, so adding a world extends
the gate automatically, and variants are applied by seeding `localStorage`
before load so the pre-paint script is the mechanism under test.

**It landed before Phase 4 deliberately, and immediately earned it: 15/20.**
Five variants failed the same way — a world's accent used *as text* on tinted
surfaces sits between 3.8:1 and 4.5:1 (fine as a fill, failing as ink). The fix
is systemic rather than twenty hand-picked values: `--color-primary-ink` blends
the accent toward the body text colour, so the correction self-adjusts per
world and polarity.

### Phase 4 — Chrome: shared header, hamburger sitemap, shared footer

One universal header (mark and tools only — every page's hero states its own
identity), one drawer carrying **every route** grouped by purpose with a role
line per entry, and one footer: *made with heart by OpenSource*.

The phase's success test — *adding a page requires deciding nothing about its
chrome* — is enforced mechanically: `e2e/chrome.spec.ts` walks `NAV_GROUPS`
itself, so a page added to `nav.ts` is in the drawer or CI fails. Full
disclosure semantics: dialog, focus trap, Esc, `aria-current`,
skip-to-content, 44px targets, reduced-motion guards.

Two bugs the preview caught, both worth the mechanism note:

- **The map bled through the drawer backdrop.** Rendered in place, the drawer
  inherits the sticky header's stacking context (z-40) and loses to Leaflet's
  panes (z≈400). It portals to `<body>` and sits on the token z-scale's top
  layer — the "never raw numbers" rule earning its keep.
- **All 48 emoji** across 17 files were replaced with lucide glyphs or plain
  text, and a guard now fails the build if one returns.

### Phase 5 — Data surfaces on tokens

echarts and cytoscape paint to `<canvas>` and cannot evaluate `var()`, so they
carried `isDark` ternaries over literal hexes. `src/lib/chartTokens.ts` resolves
the bridge tokens from the live document and re-resolves on theme change.

**A real bug surfaced by measuring**: `--chart-*` pointed at the *role* tokens
(`--ttm-control`, `--ttm-accent-cta`), and most worlds deliberately aim both at
the same colour — correct for chrome, fatal for a categorical ramp, because two
series render identically and nothing complains. Role tokens collided in **12
of 20 variants**; the raw hue tokens collide in none, and
`e2e/chart-tokens.spec.ts` asserts distinctness per variant.

Leaflet needed the same treatment plus a cache fix: its icon cache was keyed by
source alone, which would have pinned the first world's hue.

### Phase 6 — The optional site layer (`ohmgr_` prefix)

**Ships off by default.** `supabase/schema.sql` is ported with all 95
identifiers re-prefixed `ohm_` → `ohmgr_`, preserving the security model: RLS
on everything, anon limited to whitelisted `SECURITY DEFINER` RPCs, visitor and
operator tiers, `is_admin` grantable only from the SQL editor.

**The boundary is the point.** This is the *site* layer — who visited and how it
looks — and never an authorization source. `isAdmin` (application, from the
backend's `whoami`) and `isOperator` (site) stay deliberately apart, because
OHM's identity model promises offline verification with no central authority.

**Off is a first-class state, and it is enforced.** `e2e/site-layer.spec.ts`
runs in the default configuration and proves no nav entry, a real 404, no
console errors, and working device-level theme/mode with no backend at all.

The 404 turned out to be harder than it looked, and the lesson generalises:
whether the layer is enabled is a *build-time* constant, so a page-level
`notFound()` rendered the boundary while leaving the response **200** — the
page looked right and the status lied. The gate moved to `proxy.ts`, which runs
per request. The same investigation revealed `app/not-found.tsx` was still the
port's redirect-home stub, meaning unknown paths also answered 200.

### Phase 7 — Uniformity sweep, docs, CI

Card padding, section rhythm, and six near-identical spellings of one form
control collapsed onto one each. `src/test/uniformity.test.ts` then holds the
line with four guards: no raw hex, no hardcoded palette shades, site chrome
only from `Layout`, no emoji.

Worth recording: two of those guards were **wrong on first write** — a `<nav>`
inside a facet panel is correct HTML, and a checkmark in a test fixture is not
UI chrome. A guard that fails on correct code trains people to disable guards.

---

## Verification

| Gate | What it proves |
|---|---|
| `make ready` (11 gates) | Format, lint, Python tests, service↔API↔CLI parity, docs, version, lockfile, script registry |
| `npm run frontend-ready` | Typecheck, lint, 330 unit tests, build, 105 e2e |
| `e2e/themes.spec.ts` | WCAG AA across all 20 variants, from runtime-resolved values |
| `e2e/chart-tokens.spec.ts` | Chart ramp distinct in every variant |
| `e2e/chrome.spec.ts` | Sitemap completeness, focus trap, skip link, universal chrome |
| `e2e/site-layer.spec.ts` | The default (disabled) deployment is coherent |
| `e2e/settings.spec.ts` | Admin tabs still hidden without an admin key — the tripwire proving the site layer never leaked into application authorization |

## Risks, restated with hindsight

1. **Phase 1 was the whole risk**, and it was scoped to zero feature change
   precisely so failures were unambiguous. The failures it produced were all
   infrastructural (parity scraper, nginx contracts, test harness), never
   behavioural — which is what that scoping buys.
2. **Two admins was the failure mode to watch.** It never materialised because
   the vocabularies were named apart from the first line of schema.
3. **The optionality trap** — building a lovely signed-in experience and
   letting the default instance become the degraded one. The default-config
   e2e run exists to catch exactly that.
4. **First RDBMS in the repo.** No migration tooling; the schema is idempotent
   and hand-run in the Supabase SQL editor.

## Deliberately not proposed

No change to the Python backend. No component rewrite — shadcn primitives were
re-tokenized, not replaced. No new charting dependency. No change to how
application authorization works.
