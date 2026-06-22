# AssetRecord — Physical State Domain

## Decision record

OHM models two domains today:

- **Design** (`OKHManifest`) — what a device nominally is: components, specs, repair guides
- **Capability** (`ManufacturingFacility` / OKW) — what a facility can make

Repair triage requires a third: the physical state of a specific unit in the field. Without it there is no way to know that unit 7 in Hospital A has a damaged flow sensor whose housing is intact and harvestable, so salvage matching is impossible.

**Decision:** Add `AssetRecord` as a new top-level domain object following the established OKH/OKW pattern. Design stays in `OKHManifest`. Physical state lives in `AssetRecord`. The three domains form a triangle: design, capability, physical state.

**Rejected alternatives:**

- *Extend `Component` in-place* — `OKHManifest` is a shared design document. At fleet scale each unit would require its own manifest copy to record per-unit state, with no way to query across them.
- *Bare `ComponentInstance` list with no envelope* — no fleet-level query anchor; salvage matching must scan all units for a given `manifest_id`, which requires a document envelope stored and indexed under a stable key.

## Data model

File: `src/core/models/asset.py`  
Storage key: `asset/{id}.json` (consistent with `okh/{id}.json`, `okw/{id}.json`)

### `ComponentCondition`

```python
class ComponentCondition(Enum):
    INTACT  = "intact"
    DAMAGED = "damaged"
    MISSING = "missing"
    UNKNOWN = "unknown"
```

### `ComponentState`

One entry per assessed component on a physical unit.

| Field | Type | Notes |
|---|---|---|
| `component_name` | `str` | Matches `Component.name` in the referenced manifest |
| `condition` | `ComponentCondition` | Default `UNKNOWN` |
| `repair_feasible` | `Optional[bool]` | Can it be fixed in place? |
| `harvest_viable` | `Optional[bool]` | Can it be pulled for use elsewhere? |
| `source_required` | `Optional[bool]` | Must a replacement be obtained? |
| `notes` | `Optional[str]` | Technician free text |
| `observed_at` | `Optional[datetime]` | When this state was recorded |
| `assessed_by` | `Optional[str]` | Who performed the assessment |

`repair_feasible`, `harvest_viable`, and `source_required` can be derived from `condition` plus the design's `Component.replaceable`/`Component.salvageable` flags, but are stored explicitly to preserve the technician's nuanced judgment and to make salvage queries efficient.

### `AssetRecord`

One record per physical unit.

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | Auto-generated |
| `manifest_id` | `str` | UUID of the `OKHManifest` this unit is an instance of |
| `asset_tag` | `str` | Facility-assigned identifier (serial, barcode, etc.) |
| `location` | `Optional[str]` | Where this unit is deployed (hospital, floor, department) |
| `component_states` | `List[ComponentState]` | Triage results per component |
| `last_triaged_at` | `Optional[datetime]` | Set on each `record_triage` call |
| `triage_notes` | `Optional[str]` | Overall notes from the most recent triage |

## Service

File: `src/core/services/asset_service.py`  
Class: `AssetService(BaseService["AssetService"])`

Follows the same initialization pattern as `OKWService`: storage dependency via `StorageService.get_instance()`, `_ensure_domains_registered()` guard in `initialize()`.

### Methods

| Method | Signature | Notes |
|---|---|---|
| `create` | `(asset_data: Dict) -> AssetRecord` | Accepts dict or `AssetRecord` instance |
| `get` | `(asset_id: UUID) -> Optional[AssetRecord]` | |
| `list` | `(manifest_id: Optional[str] = None) -> List[AssetRecord]` | `manifest_id` scopes to one design |
| `update` | `(asset_id: UUID, patch: Dict) -> AssetRecord` | |
| `delete` | `(asset_id: UUID) -> bool` | |
| `record_triage` | `(asset_id: UUID, states: List[ComponentState], notes: Optional[str]) -> AssetRecord` | Upserts by `component_name`, sets `last_triaged_at` |

## API endpoints

Router: `src/core/api/routes/asset.py`  
Response models: `src/core/api/models/asset/response.py`  
Mounted at `/v1/api/asset`

```
POST   /                     Create asset record          → AssetResponse        201
GET    /{id}                 Get asset record             → AssetResponse        200
GET    /?manifest_id=<uuid>  List assets for a design     → AssetListResponse    200
GET    /?harvest_viable=true List harvestable components  → AssetListResponse    200
PUT    /{id}                 Update asset record          → AssetResponse        200
DELETE /{id}                 Delete asset record          → SuccessResponse      200
POST   /{id}/triage          Record triage results        → AssetResponse        200
```

### Response models

```python
class AssetResponse(BaseModel):
    id: str
    manifest_id: str
    asset_tag: str
    location: Optional[str]
    component_states: List[Dict[str, Any]]
    last_triaged_at: Optional[str]
    triage_notes: Optional[str]

class AssetListResponse(BaseModel):
    assets: List[AssetResponse]
    total: int
```

### `POST /{id}/triage` body

```json
{
  "component_states": [
    {
      "component_name": "Blood pump module",
      "condition": "damaged",
      "repair_feasible": false,
      "harvest_viable": false,
      "source_required": true,
      "notes": "Impeller cracked, housing intact",
      "assessed_by": "J. Smith"
    },
    {
      "component_name": "Pre-filter cartridge",
      "condition": "intact",
      "harvest_viable": true
    }
  ],
  "triage_notes": "Unit taken offline 2026-06-20 after flow alarm FLWERR"
}
```

## CLI

File: `src/cli/asset.py`  
Group: `ohm asset`  
All commands use `execute_with_fallback` (HTTP path + direct-service fallback).

```bash
# Create a new asset record
ohm asset create <manifest-id> --asset-tag <tag> [--location <loc>]

# Retrieve a record
ohm asset get <asset-id>

# List records, optionally filtered
ohm asset list [--manifest-id <uuid>] [--harvest-viable]

# Update top-level fields
ohm asset update <asset-id> [--asset-tag <tag>] [--location <loc>] [--triage-notes <text>]

# Delete a record
ohm asset delete <asset-id>

# Record triage results from a JSON file
ohm asset triage <asset-id> --states <json-file>

# Record a single component state inline
ohm asset triage <asset-id> \
    --component "Blood pump module" \
    --condition damaged \
    [--repair-feasible | --no-repair-feasible] \
    [--harvest-viable | --no-harvest-viable] \
    [--notes "Impeller cracked"]
```

## Integration tests

File: `tests/integration/test_api_asset.py`  
Gate: `RUN_LIVE_API_TESTS=1`

| Test class | What it covers |
|---|---|
| `TestAssetCRUD` | Create / get / list / update / delete round-trip |
| `TestAssetListFiltering` | `?manifest_id=` returns only matching records; unrelated assets excluded |
| `TestTriageRecording` | `POST /triage` merges states by `component_name` (upsert); `last_triaged_at` updates; second POST does not duplicate entries |
| `TestHarvestableFilter` | `?harvest_viable=true` returns only components where `harvest_viable=True`; `manifest_id` further scopes the result |

## Implementation order

Each PR is shippable on its own and meets the done criteria (API + CLI + docs + integration tests).

| PR | Scope |
|---|---|
| 1 | `src/core/models/asset.py` — `ComponentCondition`, `ComponentState`, `AssetRecord`, `to_dict()`, `from_dict()`, unit tests |
| 2 | `AssetService` + storage handler (`asset/{id}.json`) + integration tests for CRUD and triage |
| 3 | API router, response models, all endpoints including `?manifest_id=` and `?harvest_viable=` filters |
| 4 | `ohm asset` CLI group, all commands, `execute_with_fallback` wiring, docs |

## Relationship to the repair epic

`AssetRecord` is the foundation for two remaining repair epic items:

- **Repair triage workflow** — walks a technician through assessing each component on a unit, records a `ComponentState` per component, and surfaces a recommended action (repair in place / harvest / source new) derived from `condition` + the design's `Component.replaceable` / `Component.salvageable` flags.
- **Salvage matching** — given a needed component (by name or `part_number`), queries `AssetRecord.component_states` across all records sharing a `manifest_id` for entries where `harvest_viable=True`. Feeds into the existing supply-graph matching infrastructure.

**Parts harvesting** (next to implement) operates on manifest design components — what's listed as `replaceable` or `salvageable` in the OKH manifest itself — and does not require `AssetRecord`. Once `AssetRecord` exists, harvesting can be enriched with observed physical state.
