# MoM integration — end-to-end validation runbook

Repeatable process for verifying the Maps of Making (MoM) SPARQL integration on
**supply-graph-ai**: OHM resolving OKH manufacturing-process requirements to
Wikidata IRIs and querying MoM's public SPARQL endpoint for matching maker
spaces, instead of (or alongside) OHM's own blob-storage OKW facility data.

**Primary interaction paths (this document):**

1. **CLI** — `ohm match requirements <file> --okw-source mom` (no server required; queries MoM directly via local service code).
2. **HTTP API** — `POST /v1/api/match` with `OKW_SOURCE=mom` set in the *server's* environment.

See [`docs/matching/index.md`](../matching/index.md) for how MoM facilities flow into the
matching pipeline once loaded, and [`notes/mom-integration.md`](../../notes/mom-integration.md)
for the original design rationale (historical — written before implementation; the QID
table there is superseded by `src/config/taxonomy/processes.yaml`, the live source of truth).

---

## What this integration does

OHM's process taxonomy (`src/core/taxonomy/process_taxonomy.py` +
`src/config/taxonomy/processes.yaml`) maps a subset of canonical manufacturing
processes to **Wikidata QIDs**. MoM's own SKOS ontology (graph
`<urn:mak:ontology/mom>` at its public endpoint) maps free-text activity tags
(e.g. `"3d-printing"`, `"FDM"`, `"impression 3D"`) to the same Wikidata
entities via `owl:sameAs`. `src/core/services/mom_bridge.py` joins across
these two graphs: given an OKH manifest's required processes, it resolves each
to a Wikidata IRI via `taxonomy.get_wikidata_iri()`, then issues a SPARQL
query against MoM's endpoint to find `schema:knowsAbout`-tagged spaces that
share that IRI.

```
OKH manifest requires "3DP"
        │  taxonomy.normalize("3DP") -> "3d_printing"
        │  taxonomy.get_wikidata_iri("3d_printing") -> wikidata.org/entity/Q229367
        ▼
SPARQL query to https://mapsofmaking.org/sparql/query
        │  joins mom:knowsAbout tags -> skos:prefLabel/altLabel -> owl:sameAs -> Q229367
        ▼
List of MoM spaces (name, lat, lon) -> ManufacturingFacility stubs
        ▼
Fed into the same matching pipeline as blob-storage OKW facilities
```

No credentials are required — MoM's SPARQL endpoint is public.

### Process coverage

Only canonical processes with a `wikidata_qid` set in `processes.yaml` participate.
Spot-check what's mapped:

```bash
grep -B3 'wikidata_qid' src/config/taxonomy/processes.yaml
```

As of this writing: `3d_printing` (Q229367), `cnc_machining` (Q174689),
`cnc_milling` (Q179507), `cnc_turning` (Q1260093), `laser_cutting` (Q3062349),
`pcb_fabrication` (Q1047286), `electronics_assembly` (Q11650), `welding`
(Q12544), `painting` (Q11629). Requirements that normalize to a process
without a QID return no MoM results (not an error — `fetch_mom_facilities_for_manifest`
silently skips them; see `tests/services/test_mom_bridge.py`).

**Verify QIDs match what MoM actually has** (the QID is OHM's claim; MoM's ontology is
the source of truth for what it resolves to):

```bash
curl -s -X POST "https://mapsofmaking.org/sparql/query" \
  -H 'Accept: application/sparql-results+json' \
  --data-urlencode 'query=SELECT ?label ?qid WHERE {
    GRAPH <urn:mak:ontology/mom> {
      ?concept <http://www.w3.org/2004/02/skos/core#prefLabel>|<http://www.w3.org/2004/02/skos/core#altLabel> ?label ;
               <http://www.w3.org/2002/07/owl#sameAs> ?qid .
    }
  }' | python3 -m json.tool
```

---

## 1 — CLI demo (no server needed)

The CLI's `--okw-source mom` flag always forces local fallback matching (direct
service calls, not the HTTP API) — see `src/cli/match.py` around
`MoM as OKW source requires fallback`. This makes it the simplest way to
demo the integration: no Docker, no `.env` storage credentials.

```bash
cd supply-graph-ai
uv sync --extra dev   # once per clone / when lockfile changes

ohm match requirements synthetic_data/3d-printed-prosthetic-hand-1-0-9-okh.json \
  --okw-source mom --max-results 3 --verbose
```

This manifest's `manufacturing_processes` is `["3DP", "Post-processing", "Assembly"]` —
`3DP` normalizes to `3d_printing`, which has a MoM-mapped QID, so it produces real
matches against live MoM spaces.

**Expected (verified 2026-06-30):**

```
Status [1/3]: Loading input and preparing request
Status [2/3]: Running matching operation
Status [3/3]: Rendering output
✅ Found 3 matching facilities

Summary: 3 candidate solution(s) found.

1. FabLab Impresa Belluno - Consorzio Cultura Concept
   Confidence: 0.33
   ...
2. FAB LAB UE
   Confidence: 0.33
   ...
```

Facility names will vary between runs (3000+ MoM spaces tag `3d-printing`-equivalent
activities; OHM doesn't currently apply geographic or other filters to the MoM result
set). Confidence stays low (~0.33) because MoM space records carry only
`(name, lat, lon, processes)` — no equipment, materials, or other capability detail for
the matcher to score against; `Post-processing` and `Assembly` show as coverage gaps
since they have no Wikidata QID to resolve.

**Same demo via `OKW_SOURCE` env var** (equivalent to `--okw-source mom`; useful for
CI or scripted runs where you don't want a CLI flag):

```bash
OKW_SOURCE=mom ohm match requirements \
  synthetic_data/3d-printed-prosthetic-hand-1-0-9-okh.json --max-results 3 --json \
  -o /tmp/mom-demo.json

python3 -c "
import json
d = json.load(open('/tmp/mom-demo.json'))
print('total_solutions:', d['total_solutions'])
print([s['tree']['facility_name'] for s in d['solutions']])
"
```

> **Note:** `--json` output is written after status/log lines that also go to stdout;
> use `-o <file>` (as above) rather than piping `--json` output directly through `jq`.

---

## 2 — API demo (`OKW_SOURCE=mom` on the server)

Unlike the CLI flag, there is **no per-request override** for the API — `MatchRequest`
has no `okw_source` field. The running server's `OKW_SOURCE` environment variable is
the only switch (see `src/config/storage_config.get_okw_source()`).

### Start the server with MoM as the OKW source

```bash
cd supply-graph-ai
OKW_SOURCE=mom uv run uvicorn src.core.main:app --host 127.0.0.1 --port 8011
```

Wait for readiness:

```bash
until curl -sf http://localhost:8011/health; do sleep 2; done && echo "Ready"
```

`OKW_SOURCE=mom` takes priority over `MATCHING_LOCAL_OKW_JSON_DIR` (a local-dev
convenience that points the API at JSON files instead of blob storage) — an explicit
mom request always reaches MoM regardless of what else is set in `.env`. No need to
unset anything for this demo.

### Send a match request

The API only supports an inline `okh_manifest` or a public `okh_url` (no local file
upload) — for a quick demo, inline the manifest body:

```bash
python3 -c "
import json
d = json.load(open('synthetic_data/3d-printed-prosthetic-hand-1-0-9-okh.json'))
print(json.dumps({'okh_manifest': d, 'max_results': 3}))
" > /tmp/mom-api-body.json

curl -s -X POST "http://localhost:8011/v1/api/match" \
  -H 'Content-Type: application/json' \
  -d @/tmp/mom-api-body.json \
| python3 -c "
import json, sys
d = json.load(sys.stdin)
print('status:', d['status'])
print('total_solutions:', d['data']['total_solutions'])
for s in d['data']['solutions']:
    print(' ', s['tree']['facility_name'])
"
```

**Expected (verified 2026-06-30):** `status: success`, `total_solutions: 3`, with real
MoM space names (e.g. `MakerSpace Baiersdorf`, `FabLab Lazio Roma`, `SifaisLab` —
varies between runs).

**Confirm in server logs** that the request actually reached MoM (not blob storage):

```bash
# Look for these two lines around the request timestamp:
#   "Loading OKW facilities from MoM SPARQL endpoint"
#   "Facility candidates loaded from MoM SPARQL"
```

---

## Troubleshooting

### API ignores `OKW_SOURCE=mom` and returns synthetic/blob-storage facilities

Fixed 2026-06-30 — `_get_filtered_facilities` in `src/core/api/routes/match.py` now
checks `OKW_SOURCE` **before** `MATCHING_LOCAL_OKW_JSON_DIR`, so an explicit mom
request always wins, matching the CLI's priority (`--okw-source mom` always reaches
MoM). Previously `MATCHING_LOCAL_OKW_JSON_DIR` (commonly set in `.env` for local dev)
silently short-circuited the API straight to local JSON files before the `mom` branch
was ever reached — see `tests/unit/test_mom_okw_source_routing.py::test_get_filtered_facilities_mom_wins_over_local_json_dir`
for the regression test.

If you still see this with an older checkout: confirm server logs show `"Loading OKW
facilities from MoM SPARQL endpoint"` rather than `"Using MATCHING_LOCAL_OKW_JSON_DIR
(remote OKW listing skipped)"` — if the latter appears, pull the fix or unset
`MATCHING_LOCAL_OKW_JSON_DIR` for the server process as a workaround.

### `total_solutions: 0` / empty facility list

- Confirm the OKH manifest's `manufacturing_processes` includes at least one process
  with a `wikidata_qid` in `processes.yaml` (see *Process coverage* above). `3DP`
  (→ `3d_printing`) is a reliable choice — synthetic_data has several manifests using it.
- Confirm network reachability to `https://mapsofmaking.org/sparql/query`:
  ```bash
  curl -s -o /dev/null -w '%{http_code}\n' https://mapsofmaking.org/sparql/query
  ```
- Override the endpoint if testing against a non-default MoM deployment:
  `MOM_SPARQL_ENDPOINT=<url>` (CLI and API both honor this via `get_mom_config()`).

### Confidence scores are always low (~0.33)

Expected — see note in section 1. MoM space records carry only process tags, name,
and coordinates; OHM's matcher has no equipment/material data to compare against, so
match quality reflects process-tag overlap only.

---

## Test coverage

Unit tests exercise the bridge and taxonomy pieces without live network calls:

- `tests/services/test_mom_bridge.py` — `query_mom_spaces_for_process` /
  `fetch_mom_facilities_for_manifest` against mocked SPARQL responses (success, empty,
  no-QID short-circuit, multi-process dedup).
- `tests/unit/test_taxonomy_wikidata.py` — `ProcessDefinition.wikidata_qid`,
  `ProcessTaxonomy.get_wikidata_iri()`, YAML loading of the field.
- `tests/unit/test_mom_okw_source_routing.py` — `_get_filtered_facilities` honors
  `OKW_SOURCE=mom` (and correctly ignores it when no OKH manifest is available to
  derive required processes from).

```bash
.venv/bin/python -m pytest tests/services/test_mom_bridge.py tests/unit/test_taxonomy_wikidata.py tests/unit/test_mom_okw_source_routing.py -v
```

This is unit-level mocked coverage only — the sections above are the only live
end-to-end verification against MoM's real endpoint; no CI step currently runs them
(MoM's public endpoint and exact dataset are outside OHM's control, so we don't
gate CI on its availability or content).
