## Distributed cache (#271)

| Variable | Default | Purpose |
|----------|---------|---------|
| `CACHE_ENABLED` | `true` | Global cache gate |
| `CACHE_BACKEND` | `memory` | `memory` (single-node) or `redis` (shared) |
| `CACHE_REDIS_URL` | — | Connection URL; needed for `CACHE_BACKEND=redis` to take effect |
| `CACHE_KEY_PREFIX` | `ohm` | Namespace prefix for all keys |

`CACHE_BACKEND=redis` with no `CACHE_REDIS_URL` logs an error and falls back to
the memory backend rather than raising. The two are applied by different
mechanisms — `CACHE_BACKEND` is non-secret config in
`config/environments/<env>.toml`, `CACHE_REDIS_URL` carries credentials and is a
secretRef — so a deploy can land one before the other. Misconfiguring a
performance optimisation should cost speed, not availability. Check the startup
log to confirm which backend a replica actually selected.

**Self-host (single process):** leave defaults — no Redis required.

**Docker Compose + Redis:**

```bash
docker compose --profile redis up -d redis
# In .env:
CACHE_BACKEND=redis
CACHE_REDIS_URL=redis://redis:6379/0
docker compose up -d ohm-api
```

**ACA multi-replica:** point `CACHE_REDIS_URL` at Azure Cache for Redis, Valkey, or any Redis-protocol service. Cloud-agnostic — no Azure SDK in the cache layer.

### Why production runs Redis

`config/environments/production.toml` sets `cache_backend = "redis"`. The OKH
catalogue — every manifest, assembled once and cached — is what makes the
Designs page fast (~15s → ~2.4s cold, ~1.1s warm). With the memory backend that
cache is **per-replica**: each instance pays a full assembly on its first
request, and scaling out re-introduces the slow path for whoever lands on a new
replica. Redis shares one copy, so one assembly warms every replica.

The cached value is a list of plain dicts specifically so it survives the JSON
round trip Redis requires; caching model objects would not.

**One-time provisioning** (not done by the deploy pipeline):

Run these as written — the key is read and URL-encoded by the commands
themselves. Do not hand-substitute it: an earlier version of this page used a
`<key>` placeholder, it was pasted through unsubstituted, and Redis spent a
deployment authenticating as the literal string `<key>`. Nothing looked broken,
because a failing Redis reports cache misses.

```bash
az redis create --name ohm-cache --resource-group project_data_rg \
  --location westus3 --sku Basic --vm-size c0

# Read the key and percent-encode it (Azure keys are base64 and can contain
# "+" and "/", which change a URL's meaning if left raw).
REDIS_KEY=$(az redis list-keys --name ohm-cache --resource-group project_data_rg \
  --query primaryKey -o tsv)
REDIS_KEY_ENC=$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$REDIS_KEY")

az containerapp secret set --name openhardwaremanager --resource-group project_data_rg \
  --secrets "cache-redis-url=rediss://:${REDIS_KEY_ENC}@ohm-cache.redis.cache.windows.net:6380/0"
az containerapp update --name openhardwaremanager --resource-group project_data_rg \
  --set-env-vars CACHE_REDIS_URL=secretref:cache-redis-url
```

Then confirm it actually took, rather than assuming:

```bash
curl -s https://www.openhardwaremanager.org/v1/api/utility/metrics \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["cache"])'
```

Expect `backend: redis` **with no `error` key**, and `hits` climbing on repeat
requests. `backend: redis` alone means nothing — that is what a completely
non-functional cache reports too.

Until provisioning lands, replicas log the fallback and run the per-replica
memory cache — the pre-Redis behaviour, not an outage.

The client is synchronous and is called from async handlers, so its socket
timeout is deliberately sub-second (`SOCKET_TIMEOUT_SECONDS` in
`redis_backend.py`): a blocked lookup stalls the event loop, and waiting longer
than the assembly would defeat the purpose.

Service-level caching: use `src.core.cache.cached()` so domain services share the same backend as `@cache_response`.

Metrics: `GET /v1/api/utility/metrics` includes a `cache` object (hits, misses, backend).

Verify: `make harness-probes` → `probe_cache` clean after redis backend is enabled.
