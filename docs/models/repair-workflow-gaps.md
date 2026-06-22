# Repair Workflow Gaps

This document records the gaps between what is currently implemented and what a
complete real-world repair workflow requires. Gaps are ordered by priority: items
that break the workflow entirely come first; items that limit scale or integration
come after.

Each gap includes: what's missing, where in the codebase the fix belongs, and the
concrete change needed.

---

## Critical path gaps — workflow breaks without these

### GAP-1: `harvest_viable` is never written back from triage recommendations

**What's missing.** `GET /api/asset/{id}/triage-report` derives a `HARVEST`
recommendation for components where `condition=damaged`, `repair_feasible=False`,
and the manifest marks the component `salvageable=True`. But this recommendation
is ephemeral — it does not update the `ComponentState.harvest_viable` field on the
`AssetRecord`. The `POST /api/asset/salvage-match` endpoint only returns results
where `harvest_viable=True`, so any component the system recommends harvesting is
invisible to salvage queries unless the technician separately re-submits the triage
with the flag set explicitly.

**Effect.** The triage report and salvage matching are decoupled. A technician who
records conditions but does not re-read the report and re-submit triage will never
have their components appear in salvage search results. The loop does not close.

**Where to fix.**
- `src/core/services/asset_service.py` — `record_triage()`: after upsert, run
  `_derive_action()` for each incoming state and write back `harvest_viable`,
  `source_required`, and `repair_feasible` if not already explicitly set by the
  caller. Caller-supplied values win; derived values fill gaps.
- This keeps the technician's nuanced judgment authoritative while ensuring the
  flags are populated for any component where the caller omits them.

**API surface change.** None required. The write-back happens inside `record_triage`;
the response already returns the full updated `AssetRecord`.

---

### GAP-2: No triage checklist / session entry point

**What's missing.** A technician opening a broken device has no in-system way to
know which components to assess. The correct starting call would be something like
`GET /api/asset/{id}/triage-checklist` that returns the manifest's full component
list, pre-filled with any existing `ComponentState` entries and flagged `not_assessed`
where none exist. `GET /api/asset/{id}/triage-report` does this structurally, but
it is named and framed as output (a completed report) rather than input (a form to
fill in). In practice, calling triage-report before any triage has been recorded
returns all components with `recommended_action: "assess"` and `condition:
"not_assessed"` — which is exactly the right starting checklist — but nothing guides
a user there.

**Effect.** First-time triage on a device requires the technician to independently
fetch the OKH manifest, extract the component list, and manually construct the
`POST /api/asset/{id}/triage` body. This is error-prone and excludes any components
they don't know to ask about.

**Where to fix.**
- Option A (preferred): Rename or alias `GET /api/asset/{id}/triage-report` to also
  be reachable as `GET /api/asset/{id}/triage-checklist`, or add a `?format=checklist`
  query param that strips the summary block and formats items as fillable fields.
- Option B: Add `GET /api/asset/{id}/triage-checklist` as a distinct endpoint that
  returns the manifest component list with a `current_state` field (null if not yet
  assessed) — optimized for driving a form rather than presenting a report.
- `src/core/api/routes/asset.py` and `src/cli/asset.py` need updating in either case.

---

### GAP-3: No lifecycle / resolution state on `AssetRecord`

**What's missing.** `AssetRecord` has no field tracking the overall status of a unit
across its repair lifecycle. Once triage is recorded, the system has no way to
represent: parts ordered, repairs in progress, unit restored to service, unit
condemned. The `triage_notes` field captures free text, but there is no structured
state the system can query or filter on.

**Effect.** The fleet view cannot distinguish a unit under active repair from one
that is condemned and waiting for disposal. Salvage-match can surface components
from "condemned" units correctly (if they are marked `harvest_viable`), but there
is no way to find "all units currently awaiting parts" or "all units restored this
month."

**Where to fix.**
- `src/core/models/asset.py` — add `AssetStatus` enum:
  `active | under_triage | parts_pending | under_repair | restored | condemned`
  Default: `active`.
- `AssetRecord` — add `status: AssetStatus = AssetStatus.ACTIVE`.
- `PUT /api/asset/{id}` body (`AssetUpdateRequest`) — expose `status` as an
  updatable field.
- `GET /api/asset/` — support `?status=` filter param.
- `src/cli/asset.py` — `ohm asset update` gains `--status` option;
  `ohm asset list` gains `--status` filter.
- Migration: existing stored records will deserialize with `status=None`; `from_dict`
  should default `None` to `AssetStatus.ACTIVE`.

---

## Workflow integration gaps — pieces exist but aren't connected

### GAP-4: `RepairDocExtractor` output has no path into OKH manifests

**What's missing.** `RepairDocExtractor` extracts component names and part numbers
from repair manual PDFs (see `src/core/generation/repair_doc_extractor.py`). The
output is a dict with a `components` list. There is no CLI command or API endpoint
that takes this output and creates or patches an OKH manifest's component list.
The extracted data must be manually curated and reformatted before it can enter
the system.

**Effect.** The extraction pipeline has no downstream. Producing extraction output
is currently a terminal step rather than the first step of an ingestion workflow.

**Where to fix.**
- `src/cli/okh.py` (or a new `src/cli/repair.py`) — add
  `ohm okh import-repair-doc <pdf-path> [--manifest-id <id>]`:
  - If `--manifest-id` is given: fetch the manifest, merge extracted components
    (by name, preserving existing flags), and `PUT /api/okh/manifests/{id}`.
  - If not: create a new draft manifest from the extraction output with a
    `--draft` flag, requiring manual review before publish.
- Extracted components should have `replaceable=False`, `salvageable=False` set as
  defaults, requiring a human to annotate the repair-relevant flags. The import
  command should print a reminder to annotate these before using the manifest for
  triage.

---

### GAP-5: No sourcing resolution step connecting triage report to salvage match

**What's missing.** When the triage report returns `source_new` for one or more
components, there is no system-level step that checks fleet availability before
escalating to a procurement request. The triage report and salvage-match are two
separate calls that a human must mentally connect.

**Effect.** In practice, a repair coordinator reads the triage report, notes which
components need sourcing, then manually decides whether to run a salvage query or
go straight to procurement. For a single unit this is tolerable; at fleet scale it
means harvestable components are systematically overlooked in favor of new orders.

**Where to fix.**
- Add `POST /api/asset/{id}/resolve-sourcing`:
  - Reads the current triage report for the asset.
  - For each `source_new` item, runs `salvage_match(component_name=..., manifest_id=...)`
    excluding the asset itself.
  - Returns a resolution plan: per-component verdict of `fleet_available` (with
    matched assets) or `procure_new` (no fleet match).
- `src/cli/asset.py` — `ohm asset resolve-sourcing <asset-id>` calls this endpoint
  and prints a structured action list.
- `src/core/services/asset_service.py` — `resolve_sourcing(asset_id)` method
  orchestrates the join.

---

### GAP-6: `harvest-parts` is not enriched with actual fleet state

**What's missing.** `POST /api/okh/harvest-parts` returns design-level component
data (what the manifest says is salvageable). The implementation note in
`docs/models/asset-docs.md` explicitly says "Once AssetRecord exists, harvesting
can be enriched with observed physical state." That enrichment was not built.

**Effect.** `harvest-parts` answers "what is theoretically harvestable from this
design" but cannot answer "how many harvestable units of this component are actually
available right now." These are different questions.

**Where to fix.**
- `POST /api/okh/harvest-parts` — add optional `?enrich_fleet=true` query param.
  When set: for each component in the response, run a salvage-match query and
  attach a `fleet_available` count and list of `asset_ids` to each component dict.
- Alternatively, keep `harvest-parts` as design-only and document it as such,
  directing users to `salvage-match` for fleet-level queries. This is lower cost
  and cleaner.

---

## Scale gaps — work for one unit, break at fleet scale

### GAP-7: No reservation mechanism on harvestable components

**What's missing.** `POST /api/asset/salvage-match` returns a list of assets where
a component is `harvest_viable=True`. Nothing in the system allows a repair
coordinator to "claim" a component, marking it unavailable to concurrent queries.
Two coordinators running the same query see identical results and may both dispatch
a technician to retrieve the same component.

**Where to fix.**
- Add `ComponentState.claimed_by: Optional[str]` and `ComponentState.claimed_at:
  Optional[datetime]` fields to `src/core/models/asset.py`.
- Add `POST /api/asset/{id}/claim-component` endpoint:
  body: `{ "component_name": "...", "claimed_by": "coordinator-id" }`.
  Returns 409 Conflict if already claimed.
- `POST /api/asset/salvage-match` — add optional `?exclude_claimed=true` param
  (default true in practice).
- `ohm asset salvage-match` — `--include-claimed` flag to override.
- Claim expiry (TTL, e.g. 48h) should auto-release unclaimed reservations; a
  background job or lazy-expiry on read is sufficient.

---

### GAP-8: Salvage match is scoped to exact `manifest_id` — no compatibility mapping

**What's missing.** `salvage_match` filters assets by `manifest_id` when that
parameter is provided. Components that are physically compatible across device
variants or manufacturers are invisible if they come from a different manifest.

**Effect.** Real repair supply chains depend heavily on compatible substitutes. A
Blood pump with identical specs from a different manufacturer's device would not
appear in a query scoped to `manifest_id=X`, even if it would work.

**Where to fix.** This is the most open-ended gap. Two approaches:

- **Explicit compatibility list** (lower scope): Add a `compatible_manifest_ids:
  List[str]` field to `OKHManifest`. `salvage_match` expands the search to include
  those IDs when present. Populated manually or from the OKH `okh_ref` field on
  components.
- **Part-number-based matching** (no manifest required): `salvage_match` with only
  `part_number` set already crosses manifest boundaries — it matches any component
  with that exact part number across all assets. Documenting this as the correct
  cross-model query path may be sufficient for now.

---

## Fix sequence

Given dependencies between the gaps:

| Order | Gap | Reason |
|---|---|---|
| 1 | GAP-1 — write-back from triage → flags | Unblocks salvage-match for all non-expert users |
| 2 | GAP-3 — `AssetStatus` lifecycle field | Required before GAP-5 is meaningful |
| 3 | GAP-2 — triage checklist endpoint | Low cost; makes the system usable without docs |
| 4 | GAP-5 — sourcing resolution step | Requires GAP-1 and GAP-3 to be correct first |
| 5 | GAP-4 — RepairDoc → manifest import | Unblocks the ingestion pipeline |
| 6 | GAP-6 — fleet enrichment on harvest-parts | Low urgency; salvage-match covers the use case |
| 7 | GAP-7 — claim/reservation | Required at fleet scale; not critical for single-site |
| 8 | GAP-8 — cross-manifest compatibility | Longest-lead item; part-number workaround covers interim |
