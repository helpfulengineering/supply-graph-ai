# OHM API Fixtures — Phase 0 Contract Lock

Captured against: `http://localhost:8001` (local dev)  
Base API path: `/v1/api`  
Captured: 2026-04-07

These fixtures document the API contract for the reference frontend. They serve
as development references, contract stability anchors, and fallback data for
offline testing.

---

## Fixture Inventory

| File | Endpoint | Notes |
|---|---|---|
| `okh-list.json` | `GET /api/okh?page=1&page_size=20` | Page 1 of 20, 53 total items |
| `okh-detail.json` | `GET /api/okh/{id}` | Prosthetic Hand (rich metadata) |
| `match-response.json` | `POST /api/match` | Basic match, 5 results, no save |
| `match-response-saved.json` | `POST /api/match` | Match with `save_solution=true`, `include_human_summary=true`, `include_explanation=true` |
| `supply-tree-solutions-list.json` | `GET /api/supply-tree/solutions?page=1&page_size=10` | Paginated solution list |
| `supply-tree-solution-detail.json` | `GET /api/supply-tree/solution/{id}` | Integration test nested solution |
| `supply-tree-solution-summary.json` | `GET /api/supply-tree/solution/{id}/summary` | Real prosthetic hand solution |
| `supply-tree-visualization.json` | `GET /api/supply-tree/solution/{id}/visualization` | Real prosthetic hand (single-level) |
| `supply-tree-report.html` | `GET /api/supply-tree/solution/{id}/report` | HTML report artifact |
| `supply-tree-export-graphml.xml` | `GET /api/supply-tree/solution/{id}/export?format=graphml` | GraphML export |
| `supply-tree-export-json.json` | `GET /api/supply-tree/solution/{id}/export?format=json` | JSON export |
| `package-list.json` | `GET /api/package/list?page=1&page_size=10` | One real package: microlab |

---

## Key Demo Data IDs

| Purpose | ID |
|---|---|
| OKH hero design (Prosthetic Hand, rich) | `3f531231-bf67-4c8d-bd5f-a7ac1a86812f` |
| Saved solution from hero match | `3cc42db2-b390-4fa1-8256-dcb042a66d68` |
| Nested solution (3 nodes, 3 facilities) | `b2efdb62-6435-4805-b44b-9f64a33421c6` |
| Real package (microlab) | `fourthievesvinegar/solderless-microlab` @ `1.0.0` |

> **Note:** Hero OKH and presentation IDs are TBD — to be finalized before
> Phase 7 hardening. Current IDs are from synthetic test data.

---

## API Contract Assumptions

### OKH List — `GET /api/okh`

```
Query params:
  page         integer, default 1
  page_size    integer, default 20
  sort_by      string (field name, e.g. "title")
  sort_order   string ("asc" | "desc"), default "asc"
  filter       string (⚠ NOT WORKING — see Backend Gaps)

Response shape:
  {
    status, message, timestamp, request_id,
    pagination: { page, page_size, total_items, total_pages, has_next, has_previous },
    items: [ OKHManifest, ... ]
  }
```

Key OKH item fields for the frontend adapter:
- `id`, `title`, `version`, `repo`, `function`, `description`
- `documentation_language`, `keywords`
- `manufacturing_processes` (array of strings)
- `materials` (array)
- `design_files`, `manufacturing_files`, `making_instructions` (array of `{ title, path, type, metadata }`)
- `license.hardware`, `license.documentation`
- `licensor.name`

### Match — `POST /api/match`

```
Request body (key fields for frontend):
  okh_id            string (UUID) — preferred for demo
  max_results       integer (default 5)
  save_solution     boolean — set true to persist and get solution_id back
  solution_tags     string[] — e.g. ["demo"]
  solution_ttl_days integer — default 30
  include_human_summary  boolean — adds human_summary block to response
  include_explanation    boolean — adds per-facility explanation text

Response shape:
  {
    status, message, timestamp, request_id,
    data: {
      solution_id,         ← present when save_solution=true
      solutions: [{
        tree: { id, facility_name, okh_reference, okw_reference,
                confidence_score, materials_required, capabilities_used,
                match_type, metadata, creation_time, depth },
        facility: { id, name, location, contact, equipment,
                    manufacturing_processes, certifications, ... },
        facility_id, facility_name, match_type,
        confidence, score, metrics, rank,
        explanation,        ← dict (raw); present when include_explanation=true
        explanation_human,  ← string; human-readable match/no-match reason
      }, ...],
      total_solutions,
      matching_mode,
      processing_time,
      match_summary_text,  ← plain-text overall summary
      human_summary: {     ← present when include_human_summary=true
        profile, executive, technical, detailed, key_insights: {
          risks, opportunities, recommendations
        }
      },
      coverage_gaps, suggestions, suggestion_codes
    }
  }
```

> **Important:** `data.solution_id` is the ID to use for all supply-tree
> endpoints. It is a top-level field in `data`, NOT inside individual solutions.

### Supply Tree — Visualization

```
GET /api/supply-tree/solution/{solution_id}/visualization

Response data shape (schema_version 3.2.0):
  {
    schema_version, source_type, generated_at,
    matching: {
      overview: { matching_mode, score, tree_count }
    },
    supply_tree: {
      solution_id,
      nodes: [{ id, label, component_id, facility_name, depth,
                production_stage, confidence_score,
                estimated_cost, estimated_time }],
      edges: [{ source, target, type }],
      dependency_graph: { node_id: [dependency_ids] },
      production_sequence: [[parallel_stage_ids]],
      resource_cost: { total_estimated_cost, total_estimated_time }
    },
    network: {
      facility_distribution: [{ facility_name, tree_count }],
      route_hints: { status, note }
    },
    dashboard: {
      kpis: { tree_count, edge_count, stage_count, solution_score }
    },
    artifacts: {
      graphml_endpoint,   ← URL suffix for GraphML download
      json_bundle,        ← URL suffix for JSON export
      html_report         ← URL suffix for HTML report
    }
  }
```

### Supply Tree — Solutions List

```
GET /api/supply-tree/solutions?page=1&page_size=20
  sort_by    (field name)
  sort_order ("asc" | "desc")

Response: standard paginated wrapper
  items/result: [{
    id, okh_id, okh_title, matching_mode,
    tree_count, component_count, facility_count,
    score, created_at, updated_at, expires_at,
    ttl_days, tags, last_modified, age_days
  }]
```

### Package

```
GET /api/package/list?page=1&page_size=20

Response items: [{
  package_name,   ← format: "org/repo" (slash in name)
  version,
  okh_manifest_id,
  build_timestamp,
  total_files,
  total_size_bytes,
  build_options,
  package_path    ← server-local path (not a URL)
}]

GET /api/package/{package_name}/{version}
  ⚠ BUG: Returns 404 for known packages — see Backend Gaps

GET /api/package/{package_name}/{version}/download
  → Triggers file download (binary stream)
```

---

## Backend Gaps Identified

### GAP-1: OKH list `filter` param not implemented

- **Endpoint:** `GET /api/okh?filter=...`
- **Symptom:** Any value of `filter` returns all 53 items (no filtering applied).
- **Impact:** Frontend cannot do server-side search; search must be client-side.
- **Frontend mitigation (Phase 2):** Implement client-side title/keyword filter
  over the returned page. Works acceptably for the current 53-item dataset.
- **Backend fix needed?** Yes, for production scale. Low priority for demo.

### GAP-2: Package metadata endpoint 404

- **Endpoint:** `GET /api/package/{package_name}/{version}`
- **Symptom:** Returns `{"detail": "Not Found"}` even for
  `fourthievesvinegar/solderless-microlab/1.0.0`, which appears in the list.
- **Impact:** Package detail page cannot fetch per-package metadata from this
  endpoint.
- **Frontend mitigation:** Use the data already present in the package list
  response (`GET /api/package/list`); surface metadata from there.
- **Backend fix needed?** Yes — should be straightforward. Medium priority.

### GAP-3: No RFQ endpoint

- **Impact:** Phase 6 requires a new `/v1/api/rfq/generate` endpoint.
- **Status:** Planned as Phase 6 backend work. Frontend blocked until endpoint
  is available.

### GAP-4: Demo data is synthetic only

- **Symptom:** All 53 OKH designs in the current dataset are synthetic test
  fixtures ("3D Printed Prosthetic Hand", "Arduino-based IoT Sensor Node",
  etc.). No real-world OKH manifests are loaded.
- **Impact:** Demo narrative is weakened if shown as synthetic data.
- **Mitigation:** Load real OKH data (e.g., COVID-era designs, microlab) before
  Phase 7 hardening. Hero design TBD — to be decided with user.

### GAP-5: Single-level visualization for demo design

- **Symptom:** The prosthetic hand match produces a single-level supply tree
  (1 node, 0 edges). Cytoscape graph view will appear nearly empty.
- **Impact:** Visualization demo is weak with single-level data.
- **Mitigation options:**
  a. Use the integration test nested solution (`b2efdb62-...`, 3 nodes) for
     visualization while using real data for match/OKH views.
  b. Run a match on an OKH with `parts` sub-components and
     `auto_detect_depth=true` to generate a genuinely nested result.
  c. Generate/load richer synthetic OKH data with sub-parts.
- **Recommendation:** Evaluate at Phase 3/4 boundary when demo data is chosen.

---

## Confirmed Working

- `GET /api/okh` — pagination, sort_by, sort_order ✓
- `GET /api/okh/{id}` — full manifest detail ✓
- `POST /api/match` with `okh_id` — 5 results, ~10s response time ✓
- `POST /api/match` with `save_solution=true` — returns `data.solution_id` ✓
- `POST /api/match` with `include_human_summary=true` + `include_explanation=true` ✓
- `GET /api/supply-tree/solutions` — paginated list ✓
- `GET /api/supply-tree/solution/{id}` — solution detail ✓
- `GET /api/supply-tree/solution/{id}/summary` ✓
- `GET /api/supply-tree/solution/{id}/visualization` — schema 3.2.0 ✓
- `GET /api/supply-tree/solution/{id}/report` — HTML artifact ✓
- `GET /api/supply-tree/solution/{id}/export?format=graphml` ✓
- `GET /api/supply-tree/solution/{id}/export?format=json` ✓
- `GET /api/package/list` ✓
