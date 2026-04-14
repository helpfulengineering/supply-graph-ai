# Match endpoint — end-to-end validation runbook

Repeatable process for verifying `POST /v1/api/match` on **supply-graph-ai**.

**Primary interaction paths (this document):**

1. **HTTP API** — `curl` or any HTTP client (same contract as production integrations).
2. **CLI** — `ohm match requirements …` calls the same `/v1/api/match` endpoint when the server is reachable.

**Optional:** a small Node script in `project-data-platform-ts` can sanity-check the same JSON body the browser sends; see [Optional: frontend parity check](#optional-frontend-parity-check).

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Docker Desktop running | `docker info` must succeed |
| Network access to Azure Blob Storage | `projdatablobstorage.blob.core.windows.net` |
| `.env` in `supply-graph-ai/` | Azure credentials and `AZURE_STORAGE_*` |
| **For CLI:** Python 3.12+ and editable install | `pip install -e .` from `supply-graph-ai` (installs the `ohm` command) |

Node.js is **not** required unless you use the optional frontend script.

---

## 1 — Start the backend

The API must be up before any match request.

```bash
cd supply-graph-ai

# First-time or after code changes: build the image
docker compose build ohm-api

# Start (or restart) the container
docker compose up -d --force-recreate ohm-api
```

> **Important:** use `--force-recreate` so the container picks up the latest
> image and `.env`. Plain `docker compose up -d` can leave a stale container
> running old code.

Wait until the health check passes (often ~20 s while spaCy loads):

```bash
until curl -sf http://localhost:8001/health; do sleep 3; done && echo "Ready"
```

Expected:

```json
{"status":"ok","domains":["cooking","manufacturing"],"version":"1.0.0"}
```

---

## 2 — Canonical demo: HTTP API + CLI (same logical request)

Use a public OKH URL (same pattern as the frontend: **`okh_url` only**).

**Variables (reuse in both sections):**

```bash
export OHM_BASE=http://localhost:8001
export OKH_URL='https://projdatablobstorage.blob.core.windows.net/okh/okh-chococolate-chip-cookies-recipe.json'
```

### 2a — HTTP API (`curl`)

Minimal POST (JSON body matches `MatchRequest`: `okh_url`):

```bash
curl -s -X POST "${OHM_BASE}/v1/api/match" \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d "{\"okh_url\":\"${OKH_URL}\"}"
```

**Expected:** HTTP `200`, JSON `status` = `"success"`, `data.total_solutions` ≥ `2` for the current team Azure data (two kitchen OKWs).

Optional query parameters are passed in the JSON body, for example:

```bash
curl -s -X POST "${OHM_BASE}/v1/api/match" \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d "{\"okh_url\":\"${OKH_URL}\",\"min_confidence\":0.05,\"max_results\":5}"
```

### 2b — CLI equivalent (`ohm match requirements`)

The CLI issues **`POST {server}/v1/api/match`** when you pass an **https** URL as the first argument: it sends `okh_url` (initial domain `manufacturing`; the server re-detects cooking from the manifest).

From the **host** (not inside Docker), with the repo installed:

```bash
cd supply-graph-ai
pip install -e .   # once per environment

# Point at the running API (global flag on `ohm`)
ohm --server-url "${OHM_BASE}" match requirements "${OKH_URL}" --json
```

**CLI flags that mirror the API body:**

| API field (`MatchRequest`) | CLI flag |
|---|---|
| `min_confidence` | `--min-confidence` (default **0.1**, aligned with API) |
| `max_results` | `--max-results` |
| `max_depth` | `--max-depth` |
| `domain` | `--domain manufacturing\|cooking` (usually omit; server infers cooking from OKH content for URLs) |

Pretty-printed JSON to a file:

```bash
ohm --server-url "${OHM_BASE}" match requirements "${OKH_URL}" \
  --json -o /tmp/match-cookies.json
```

**Local OKH file instead of URL:** the CLI reads the file and sends `okh_manifest` in the request body (still hits the same endpoint). Equivalent to downloading the manifest yourself and POSTing it—**not** the same as `okh_url`, but useful offline:

```bash
curl -s -o /tmp/cookies.okh.json "${OKH_URL}"
ohm --server-url "${OHM_BASE}" match requirements /tmp/cookies.okh.json --json
```

> **Note:** for URL inputs the CLI defaults the *initial* domain to manufacturing
> and passes `okh_url`; the API then re-routes to cooking when the manifest
> looks like a recipe. You normally do **not** need `--domain cooking` for blob
> OKH URLs.

---

## 3 — Inspect solutions (API vs CLI)

### API — summary fields with `curl` + `python3`

```bash
curl -s -X POST "${OHM_BASE}/v1/api/match" \
  -H 'Content-Type: application/json' \
  -d "{\"okh_url\":\"${OKH_URL}\"}" \
| python3 -c "
import sys, json
d = json.load(sys.stdin)
print('status:', d.get('status'))
print('total_solutions:', d['data']['total_solutions'])
for s in d['data']['solutions']:
    meta = s.get('tree', {}).get('metadata', {}) if isinstance(s.get('tree'), dict) else {}
    print(f\"  {s['facility_name']}  confidence={s['confidence']:.3f}\")
    print(f\"    ingredient_overlap={meta.get('ingredient_overlap','?')}/{meta.get('ingredient_count','?')}\")
    print(f\"    tool_overlap={meta.get('tool_overlap','?')}/{meta.get('tool_count','?')}\")
"
```

### CLI — same data in `--json` output

With `--json`, the CLI prints the **same object as the API’s `data` field** (not the outer `{ status, message, data }` envelope): top-level keys include `solutions`, `total_solutions`, `matching_mode`, etc.

```bash
ohm --server-url "${OHM_BASE}" match requirements "${OKH_URL}" --json \
| jq '.solutions[] | {facility_name, confidence, match_type}'
```

To compare with `curl`, either pipe the API response through `jq '.data'` first or query `.data` in one shot:

```bash
curl -s -X POST "${OHM_BASE}/v1/api/match" \
  -H 'Content-Type: application/json' \
  -d "{\"okh_url\":\"${OKH_URL}\"}" \
| jq '.data | {total_solutions, solution_names: [.solutions[].facility_name]}'
```

---

## 4 — Different OKH targets

**API — any public `okh_url`:**

```bash
curl -s -X POST "${OHM_BASE}/v1/api/match" \
  -H 'Content-Type: application/json' \
  -d '{"okh_url":"https://projdatablobstorage.blob.core.windows.net/okh/my-other-file.json"}'
```

**CLI — same URL:**

```bash
ohm --server-url "${OHM_BASE}" match requirements \
  'https://projdatablobstorage.blob.core.windows.net/okh/my-other-file.json' --json
```

---

## Optional: frontend parity check

`project-data-platform-ts` includes a script that sends the same shape as Nuxt (`{ okh_url }` only). **Requires Node ≥ 18.**

```bash
cd project-data-platform-ts
OKH_FNAME=okh-chococolate-chip-cookies-recipe.json node scripts/verify-ohm-match.mjs
```

Set `VITE_SUPPLY_GRAPH_AI_URL` if the API is not on `http://localhost:8001`.

---

## Troubleshooting

### `total_solutions: 0` — empty result set

#### A. Stale Docker image

```bash
cd supply-graph-ai
docker compose ps
docker compose build ohm-api && docker compose up -d --force-recreate ohm-api
```

Confirm domain re-detection code is in the image:

```bash
docker exec ohm-api grep -c "_detect_domain_from_manifest" /app/src/core/api/routes/match.py
# Expect 2; 0 means stale image
```

#### B. CLI talks to the wrong server

```bash
ohm --server-url http://localhost:8001 system health
```

This hits `{server-url}/health` (same host/port you use for `curl`). If it fails,
fix `--server-url` or your shell environment before retrying `match requirements`.

The CLI builds requests to **`{server-url}/v1/api/match`**. Override with
`--server-url` or set `OME_SERVER_URL` (see `src/cli/base.py`; some docs
refer to `OHM_SERVER_URL` — if in doubt, use `--server-url`).

#### C. Azure / pipeline logs

```bash
docker compose logs ohm-api -f
```

| Log message | Meaning |
|---|---|
| `Detected domain: manufacturing` | Initial routing from `okh_url` (expected) |
| `Re-detected domain as cooking from OKH manifest content` | Server switched to cooking ✓ |
| `Listing kitchen capabilities` | Loading kitchen OKWs ✓ |
| `Found N unique kitchen capabilities` | N kitchens found ✓ |
| `Enhanced matching completed: N results` | Matcher produced N raw results |
| `Processed matching results: M solutions` | After `min_confidence` / `max_results` |

**`Processed matching results: 0`** but **`Enhanced matching completed: N>0`:** raise
`min_confidence` in the API body or lower it to confirm:

```bash
curl -s -X POST "${OHM_BASE}/v1/api/match" \
  -H 'Content-Type: application/json' \
  -d "{\"okh_url\":\"${OKH_URL}\",\"min_confidence\":0.05}"
```

```bash
ohm --server-url "${OHM_BASE}" match requirements "${OKH_URL}" --min-confidence 0.05 --json
```

#### D. Storage configuration

Check `.env`:

```
STORAGE_PROVIDER=azure_blob
AZURE_STORAGE_ACCOUNT=projdatablobstorage
AZURE_STORAGE_CONTAINER=newformats
AZURE_STORAGE_OKW_CONTAINER_NAME=okw
```

### Container fails to start

```bash
docker compose logs ohm-api --tail 80
```

Typical causes: missing `AZURE_STORAGE_KEY`, or image build incomplete (re-run `docker compose build ohm-api`).

---

## How the pipeline works (summary)

```
curl / ohm CLI / optional frontend script
         │
         ▼
POST /v1/api/match   { "okh_url": "<public https URL>" }
         │
         ▼
supply-graph-ai
  1. Fetch OKH from okh_url
  2. Re-detect domain (e.g. cooking from manifest content)
  3. List OKW files from configured Azure container/prefix
  4. Match requirements vs capabilities; compute confidence
  5. Apply min_confidence / max_results
  6. Return { data: { solutions, total_solutions, ... } }
```

---

## Known data quality notes

Kitchen OKWs under `newformats/okw/` may list partial `ingredients` / `tools` /
`appliances`. Confidence reflects overlap with the recipe; fuzzy substring
matching helps (e.g. `"sugar"` vs `"brown sugar"`). Enrich OKW JSON in Azure
to raise scores.

| Kitchen (cookie recipe) | Approx. confidence | Notes |
|---|---|---|
| Butler Kitchen | ~0.30 | Stronger overlap |
| Rob's Dessert Kitchen | ~0.23 | Still above default 0.1 threshold |
