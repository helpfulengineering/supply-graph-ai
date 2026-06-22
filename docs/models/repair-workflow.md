# Repair Workflow

OHM's repair workflow lets coordinators track physical device units in the field,
triage their condition against the OKH design, find salvageable parts across the
fleet, and route components to the technicians who need them.

## Concepts

| Term | Meaning |
|---|---|
| **AssetRecord** | A physical device unit linked to an OKH manifest. Stores per-component condition observations. |
| **Triage** | Recording observed component states (intact / damaged / missing / unknown) for a specific unit. |
| **Triage report** | Derived recommendation for each component: repair, harvest, source new, or no action. |
| **Salvage match** | Fleet-wide query for components marked `harvest_viable` that match a part need. |
| **Claim** | Reservation placed by a coordinator on a specific harvested component, preventing concurrent allocation. |
| **Compatible manifests** | Two manifests declared interchangeable — salvage-match searches across both when scoped to either. |

---

## Data model

File: `src/core/models/asset.py`  
Storage key pattern: `asset/{id}.json`

### `AssetRecord`

```
id                  UUID (auto-generated)
manifest_id         UUID of the linked OKH manifest
asset_tag           Human-readable label (serial number, QR code, etc.)
location            Physical location string
status              Lifecycle status (see below)
component_states    List[ComponentState]
last_triaged_at     ISO-8601 timestamp of most recent triage
triage_notes        Free-text session notes
```

### Lifecycle status (`AssetStatus`)

```
active          Device is in service — no repair work needed
under_triage    Currently being assessed
parts_pending   Triage complete; waiting for replacement parts
under_repair    Active repair in progress
restored        Repair complete, device returned to service
condemned       Beyond economical repair; flagged for parts harvest
```

### `ComponentState`

```
component_name      Matches a Component.name in the linked manifest
condition           intact | damaged | missing | unknown
harvest_viable      bool — derived from condition + manifest flags, can be overridden
repair_feasible     bool — technician override
source_required     bool — derived from condition + manifest flags
notes               Free-text observation
assessed_by         Identifier of the technician
observed_at         ISO-8601 timestamp
claimed_by          Coordinator ID (set by claim-component)
claimed_at          ISO-8601 timestamp of claim
```

`harvest_viable`, `repair_feasible`, and `source_required` are **auto-derived** on every
`POST /{id}/triage` call based on `condition` + the manifest's `salvageable`, `replaceable`,
and `consumable` flags. Explicit caller-supplied values always win over derived defaults
(GAP-1 fix).

---

## Complete workflow

### Step 1 — Register device units

```bash
# API
POST /v1/api/asset/
{
  "manifest_id": "<okh-uuid>",
  "asset_tag": "VEN-FIELD-007",
  "location": "Bay 1 — Triage"
}

# CLI
ohm asset create --manifest-id <uuid> --asset-tag VEN-FIELD-007 --location "Bay 1"
```

### Step 2 — Start a triage session

Retrieve the checklist to see which components need assessment:

```bash
# API
GET /v1/api/asset/{id}/triage-checklist

# CLI
ohm asset triage-checklist <asset-id>
```

Response fields:
- `assessed_count` / `pending_count` — session progress
- `items[].assessed` — whether a ComponentState exists for this component
- `items[].current_condition` — what was recorded, or null
- `items[].replaceable`, `salvageable`, `consumable` — from the manifest

### Step 3 — Record observations

```bash
# API
POST /v1/api/asset/{id}/triage
{
  "component_states": [
    { "component_name": "Blower Motor", "condition": "damaged" },
    { "component_name": "Control Board", "condition": "intact" },
    { "component_name": "Flow Control Valve", "condition": "missing" }
  ],
  "triage_notes": "Unit dropped; motor casing cracked"
}

# CLI
ohm asset triage <asset-id> \
  --component "Blower Motor" --condition damaged \
  --component "Control Board" --condition intact \
  --component "Flow Control Valve" --condition missing \
  --notes "Unit dropped; motor casing cracked"
```

OHM auto-derives:
- `harvest_viable=true` for the Blower Motor if the manifest marks it `salvageable`
- `source_required=true` for the Flow Control Valve if the manifest marks it `replaceable`

### Step 4 — Generate a repair report

```bash
# API
GET /v1/api/asset/{id}/triage-report

# CLI
ohm asset triage-report <asset-id>
```

Per-component `recommended_action` values:

| Action | Meaning |
|---|---|
| `assess` | Not yet triaged or condition unknown |
| `no_action` | Intact — no work needed |
| `repair_in_place` | Damaged but technician marked `repair_feasible` |
| `harvest` | Damaged/missing, manifest marks it `salvageable` |
| `source_new` | Damaged/missing, manifest marks it `replaceable` |
| `decommission` | Damaged/missing, neither salvageable nor replaceable |

### Step 5 — Find available parts in the fleet (salvage-match)

```bash
# API
POST /v1/api/asset/salvage-match
{
  "component_name": "Blower Motor",
  "manifest_id": "<okh-uuid>",
  "exclude_claimed": true
}

# CLI
ohm asset salvage-match --component-name "Blower Motor" --manifest-id <uuid>
```

To also search across physically compatible device types, first link manifests
(see Step 7), then scope the query to the primary manifest — OHM automatically
expands the search to compatible manifests.

### Step 6 — Claim a component

```bash
# API
POST /v1/api/asset/{id}/claim-component
{ "component_name": "Blower Motor", "claimed_by": "coord-alice" }

# CLI
ohm asset claim-component --asset-id <uuid> --component-name "Blower Motor" --claimed-by coord-alice
```

Returns **409 Conflict** if already claimed. Claims expire after 48 hours
(lazy-checked on next read).

### Step 7 — Resolve sourcing for components not available in-fleet

```bash
# API
GET /v1/api/asset/{id}/resolve-sourcing

# CLI
ohm asset resolve-sourcing <asset-id>
```

For every component the triage report marks `source_new`, OHM checks whether a
harvestable fleet match exists before returning a `procure_new` verdict. Response
fields:
- `fleet_available_count` — components resolvable from fleet
- `procure_new_count` — components that must be procured externally
- `items[].verdict` — `fleet_available` or `procure_new`
- `items[].matches` — list of assets carrying a harvestable instance

---

## Compatible manifests (cross-model salvage)

Two OKH manifests can be declared physically compatible when their components
are interchangeable (same pump family across ventilator and CPAP lines, for example).
Once linked, `salvage-match` with `manifest_id=<primary>` automatically searches
assets from both manifests.

```bash
# API — set on the manifest via PUT
GET /v1/api/okh/{primary-id}
# copy the JSON, add compatible_manifest_ids, then:
PUT /v1/api/okh/{primary-id}
{
  ...,
  "compatible_manifest_ids": ["<compat-id>"]
}

# CLI
ohm okh set-compatible-manifests <primary-id> <compat-id-1> [<compat-id-2> ...]
ohm okh set-compatible-manifests <primary-id> --add <compat-id>
ohm okh set-compatible-manifests <primary-id> --remove <compat-id>
ohm okh set-compatible-manifests <primary-id> --clear
```

---

## Fleet-level harvest inventory (harvest-parts)

Retrieve a flat component list from one or more manifests with live fleet
availability counts attached:

```bash
# API
POST /v1/api/okh/harvest-parts
{
  "manifest_ids": ["<id-1>", "<id-2>"],
  "replaceable_only": true,
  "enrich_fleet": true
}

# CLI
ohm okh harvest-parts <id-1> <id-2> --replaceable-only --enrich-fleet
```

With `enrich_fleet=true`, each component in the response includes:
- `fleet_available_count` — number of assets with a harvestable instance
- `fleet_asset_ids` — list of asset UUIDs

---

## OKH repair-doc extraction

Import repair information from service manuals or parts catalogs into an existing
OKH manifest:

```bash
# Extract repair fields from a PDF (offline, no LLM required)
ohm okh extract-repair-docs fresenius-service-manual.pdf

# Merge the extracted patch into a stored manifest
ohm okh import-repair-doc fresenius-service-manual.pdf --manifest-id <uuid>

# API equivalent
POST /v1/api/okh/extract-repair-docs   (multipart/form-data)
POST /v1/api/okh/import-repair-doc     (multipart/form-data)
```

---

## API response conventions

Asset endpoints follow a slightly different naming convention from OKH/OKW endpoints:

| Field | OKH/OKW endpoints | Asset endpoints |
|---|---|---|
| `status` | API response status (`"success"`) | **Device lifecycle status** (`"active"`, `"under_triage"`, …) |
| `message` | Human-readable API message | Human-readable API message (same) |

Every asset endpoint response includes a `message` field with a human-readable
summary (e.g. `"Triage recorded"`, `"3 harvestable match(es) found"`).
HTTP status codes are the primary signal for API success/failure — `2xx` means
success, `4xx` means a client error, `5xx` means a server error.
