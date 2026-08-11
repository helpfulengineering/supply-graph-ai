---
title: Deploy a cooking-domain instance
area: selfhost
surface: selfhost
---

# Deploy a cooking-domain instance

A cooking-domain instance is an ordinary OHM deployment (see
[Deploy a node on Azure](deploy-a-node-on-azure.md) or
[Run your own node](run-your-own-node.md)) pointed at recipe/kitchen data
instead of hardware designs and facilities. There is no separate build,
image, or code path — matching, storage, and the API are identical. Only
configuration differs.

## What makes it a cooking instance

| Setting | Manufacturing (default) | Cooking |
|---------|--------------------------|---------|
| `OHM_DEFAULT_DOMAIN` | `manufacturing` (or unset) | `cooking` |
| Storage bucket contents | OKH manifests / OKW facilities under `okh/` / `okw/` | Recipes / kitchens under the same `okh/` / `okw/` prefixes |

Recipe and kitchen records live in the **same bucket and prefixes** as OKH
manifests and OKW facilities — content is distinguished by shape, not
location. See `Recipe.is_cooking_recipe()` and
`KitchenCapability.is_cooking_capability()` in
`src/core/domains/cooking/models.py`. Pointing an instance at "a bucket with
the relevant recipes and kitchens" needs no new storage mechanism: the
existing `STORAGE_PROVIDER` / `AZURE_STORAGE_*` (or S3/GCS equivalent) env
vars already used for manufacturing data do the whole job.

`OHM_DEFAULT_DOMAIN` only changes what a **fresh browser tab** opens to
(`GET /api/utility/domains` → `default_domain`) — it does not restrict the
API. Manufacturing OKH/OKW endpoints keep working on a cooking instance and
vice versa; the setting is a UI convenience, not an access boundary.

## Configure the environment

Add to the environment's `config/environments/<environment>.toml` (see
`deploy_env_vars()` in `src/config/schema.py` — any scalar key in this file
becomes an upper-cased env var on deploy, no schema change required):

```toml
ohm_default_domain = "cooking"

storage_provider = "azure_blob"
azure_storage_account = "..."
azure_storage_container = "..."   # a container holding recipe/kitchen JSON
```

`azure_storage_key` (or the equivalent secret for another provider) stays a
secret — set it via `--mirror-secrets-from` or a Key Vault reference, never
in the TOML file. See [Deploy a node on Azure](deploy-a-node-on-azure.md) for
the full secrets story.

Then deploy as usual:

```bash
python deploy/scripts/deploy_azure.py \
  --environment <environment> \
  --image touchthesun/openhardwaremanager:<version> \
  --subscription-id <subscription-id>
```

## Upload recipe and kitchen data

Recipes and kitchens are read-only browse/match data — there is no create
UI or CLI by design (`ohm okh list-recipes`, `ohm okw list-kitchens` are
list-only). Upload correctly-shaped JSON directly to the bucket's `okh/` and
`okw/` prefixes:

```json title="okh/sourdough-bread.json"
{
  "id": "5b1f7e2a-...",
  "name": "Sourdough Bread",
  "ingredients": ["flour", "water", "salt", "starter"],
  "instructions": ["Mix", "Bulk ferment", "Shape", "Bake"],
  "equipment": ["oven", "mixing bowl"]
}
```

```json title="okw/home-kitchen.json"
{
  "id": "9c4a3d10-...",
  "name": "Home Kitchen",
  "appliances": ["oven", "stovetop"],
  "tools": ["mixing bowl", "knife"],
  "ingredients": ["flour", "water", "salt", "starter", "yeast"]
}
```

## Verify

1. `GET /api/utility/domains` returns `"default_domain": "cooking"`.
2. `GET /api/okh/recipes` and `GET /api/okw/kitchens` list the uploaded
   records (also reachable via `ohm okh list-recipes` / `ohm okw
   list-kitchens`).
3. `POST /api/match` with an inline `recipe` and `okw_facilities` (kitchen
   dicts) returns a real match — the matching engine already accepts this
   shape; see `_extract_recipe()` in `src/core/api/routes/match.py`.

## Tear down

Cooking instances stood up for an experiment are disposable. Remove them
with:

```bash
python deploy/scripts/teardown_azure_environment.py --environment <environment> --yes
```

The script refuses to touch `production` by design.
