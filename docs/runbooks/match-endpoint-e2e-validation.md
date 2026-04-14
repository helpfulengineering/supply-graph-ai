# Match endpoint — end-to-end validation runbook

Repeatable process for verifying the `POST /v1/api/match` integration between
`project-data-platform-ts` (frontend) and `supply-graph-ai` (backend).

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Docker Desktop running | `docker info` must succeed |
| Node ≥ 18 | For the verification script |
| Network access to Azure Blob Storage | `projdatablobstorage.blob.core.windows.net` |
| `.env` present in `supply-graph-ai/` | Contains Azure credentials |

---

## 1 — Start the backend

The backend must be running before any match request is made.

```bash
cd supply-graph-ai

# First-time or after code changes: build the image
docker compose build ohm-api

# Start (or restart) the container
docker compose up -d --force-recreate ohm-api
```

> **Important:** always use `--force-recreate` so the container picks up the
> latest image and `.env` values.  Plain `docker compose up -d` reuses an
> existing container and may run stale code even after a rebuild.

Wait until the health check passes (takes ~20 s while spaCy models load):

```bash
# Poll until HTTP 200
until curl -sf http://localhost:8001/health; do sleep 3; done && echo "Ready"
```

Expected response:
```json
{"status":"ok","domains":["cooking","manufacturing"],"version":"1.0.0"}
```

---

## 2 — Run the frontend verification script

`project-data-platform-ts` ships a script that fires exactly the same request
shape the Nuxt app uses.

```bash
cd project-data-platform-ts

# Cookie-recipe demo (OKH file already in Azure `okh` container)
OKH_FNAME=okh-chococolate-chip-cookies-recipe.json node scripts/verify-ohm-match.mjs
```

**Expected output:**
```
Request URL: http://localhost:8001/v1/api/match
Request body: {"okh_url":"https://projdatablobstorage.blob.core.windows.net/okh/okh-chococolate-chip-cookies-recipe.json"}
HTTP 200 OK
Response envelope: {
  status: 'success',
  message: 'Matching completed successfully',
  total_solutions: 2,
  solutions_length: 2
}
OK: match request matches front-end contract and returned HTTP 200.
```

Any other `total_solutions` or a non-zero exit code indicates a problem —
see the **Troubleshooting** section below.

---

## 3 — Optional: inspect solution detail via curl

```bash
curl -s -X POST http://localhost:8001/v1/api/match \
  -H 'Content-Type: application/json' \
  -d '{"okh_url":"https://projdatablobstorage.blob.core.windows.net/okh/okh-chococolate-chip-cookies-recipe.json"}' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('total_solutions:', d['data']['total_solutions'])
for s in d['data']['solutions']:
    meta = s.get('tree', {}).get('metadata', {}) if isinstance(s.get('tree'), dict) else {}
    print(f\"  {s['facility_name']}  confidence={s['confidence']:.3f}\")
    print(f\"    ingredient_overlap={meta.get('ingredient_overlap','?')}/{meta.get('ingredient_count','?')}\")
    print(f\"    tool_overlap={meta.get('tool_overlap','?')}/{meta.get('tool_count','?')}\")
"
```

---

## 4 — Using a different OKH file

Set `OKH_URL` to the full public blob URL, or `OKH_FNAME` to the filename
inside the `okh` container:

```bash
# By filename
OKH_FNAME=my-other-recipe.json node scripts/verify-ohm-match.mjs

# By full URL
OKH_URL=https://projdatablobstorage.blob.core.windows.net/okh/my-file.json \
  node scripts/verify-ohm-match.mjs
```

---

## Troubleshooting

### `total_solutions: 0` — empty result set

Work through the checklist in order:

#### A. Is the container running the latest image?

```bash
cd supply-graph-ai
docker compose ps          # container should show "Up"
docker compose build ohm-api && docker compose up -d --force-recreate ohm-api
```

Verify the domain re-detection patch is present in the running container:

```bash
docker exec ohm-api grep -c "_detect_domain_from_manifest" \
  /app/src/core/api/routes/match.py
# Must print 2; if it prints 0, the image is stale — rebuild above
```

#### B. Does the container reach Azure Storage?

Tail the logs for a request:

```bash
docker compose logs ohm-api -f &
# (trigger a request in another terminal)
```

Look for these log lines in order — each confirms a stage of the pipeline:

| Log message | What it means |
|---|---|
| `Detected domain: manufacturing` | Request received; initial detection (expected) |
| `Re-detected domain as cooking from OKH manifest content` | Manifest inspected; domain corrected to cooking ✓ |
| `Listing kitchen capabilities` | OKW service called for cooking domain ✓ |
| `Found N unique kitchen capabilities` | N kitchen OKW files loaded from Azure ✓ |
| `Filtered facilities: N out of N` | Facilities passed filter ✓ |
| `Enhanced matching completed: N results` | Matcher produced N candidates ✓ |
| `Processed matching results: N solutions` | Final count after confidence threshold |

**If `Re-detected domain as cooking` is missing:** the OKH manifest did not
trigger cooking detection.  Check that the manifest has at least one of:
- `domain: "cooking"` field
- `manufacturing_processes` containing only cooking terms (bake, mix, etc.)
- A `function` field with a cooking keyword plus `tool_list` or `making_instructions`

**If `Found 0 unique kitchen capabilities`:** no kitchen OKW files are visible
in the configured storage container.  Verify `.env`:
```
STORAGE_PROVIDER=azure_blob
AZURE_STORAGE_ACCOUNT=projdatablobstorage
AZURE_STORAGE_CONTAINER=newformats        # contains ButlerKitchen.json etc.
AZURE_STORAGE_OKW_CONTAINER_NAME=okw     # path prefix inside container
```

**If `Processed matching results: 0 solutions`** after `Enhanced matching
completed: N results`: the confidence filter is removing all candidates.
The default threshold is `min_confidence=0.1`.  Pass a lower value explicitly
to confirm:

```bash
curl -s -X POST http://localhost:8001/v1/api/match \
  -H 'Content-Type: application/json' \
  -d '{"okh_url":"https://projdatablobstorage.blob.core.windows.net/okh/okh-chococolate-chip-cookies-recipe.json","min_confidence":0.05}'
```

If solutions appear with a lower threshold, the kitchen OKW files have sparse
capability data.  Update the files in Azure to add more `ingredients`,
`tools`, and `appliances` so matches score above 0.1.

### Container crashes / fails to start

```bash
docker compose logs ohm-api --tail 50
```

Common causes:
- Missing `.env` or missing `AZURE_STORAGE_KEY`
- spaCy model not downloaded inside the image (re-run `docker compose build`)

### `node: not found` when running the verify script

Install Node.js ≥ 18 or use `npx node@18`:
```bash
npx --yes node@18 scripts/verify-ohm-match.mjs OKH_FNAME=okh-chococolate-chip-cookies-recipe.json
```

---

## How the pipeline works (summary)

```
frontend                           supply-graph-ai
───────                            ───────────────
POST /v1/api/match
  { okh_url: "...blob.../okh/...json" }
                          ──────────►
                                   1. Fetch OKH manifest from okh_url
                                   2. Inspect manifest fields → detect domain
                                      (cooking if manufacturing_processes = ["bake"] etc.)
                                   3. Load kitchen OKW files from Azure (newformats/okw/)
                                   4. For each kitchen:
                                      - Extract capabilities (ingredients, tools, appliances)
                                      - Fuzzy-match against recipe requirements
                                      - Compute confidence score (0–1)
                                   5. Filter by min_confidence (default 0.1)
                                   6. Return solutions sorted by confidence
          ◄──────────────────────
  { data: { solutions: [...], total_solutions: 2 } }

frontend renders facility cards
with facility_name + confidence
```

---

## Known data quality notes

The kitchen OKW files in Azure (`newformats/okw/`) currently have partial
ingredient and tool lists.  Confidence scores reflect actual overlap:

| Kitchen | Confidence (cookie recipe) | Notes |
|---|---|---|
| Butler Kitchen | ~0.30 | flour, sugar, chocolate chips match; spatula matches |
| Rob's Dessert Kitchen | ~0.23 | flour, sugar match; spatula matches |

The matching engine uses **fuzzy substring matching** (e.g. `"sugar"` in
kitchen matches `"brown sugar"` in recipe, `"chocolate chips"` matches
`"chocolate chip"`).  To improve scores, add more ingredients and appliances
to the kitchen OKW files in the `newformats` container.
