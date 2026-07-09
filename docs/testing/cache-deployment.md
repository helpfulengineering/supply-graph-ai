## Distributed cache (#271)

| Variable | Default | Purpose |
|----------|---------|---------|
| `CACHE_ENABLED` | `true` | Global cache gate |
| `CACHE_BACKEND` | `memory` | `memory` (single-node) or `redis` (shared) |
| `CACHE_REDIS_URL` | — | Required when `CACHE_BACKEND=redis` |
| `CACHE_KEY_PREFIX` | `ohm` | Namespace prefix for all keys |

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

Service-level caching: use `src.core.cache.cached()` so domain services share the same backend as `@cache_response`.

Metrics: `GET /v1/api/utility/metrics` includes a `cache` object (hits, misses, backend).

Verify: `make harness-probes` → `probe_cache` clean after redis backend is enabled.
