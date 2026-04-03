# LLM Chunked Mode

Chunked mode is a feature of the LLM generation layer that prevents context-limit errors when processing large repositories. It activates automatically when the estimated token count of a prompt exceeds the configured chunk budget, replacing a single large prompt with a map-reduce workflow: the input is split into overlapping chunks, each chunk is processed independently (map stage), and the results are synthesized into a final manifest (reduce stage).

## Why it exists

The default `LLMService.generate(prompt=...)` path passes a single string to the provider. Repositories with large READMEs, dense file trees, or lengthy JSON metadata can exceed the provider's context window. When this happens, the API either returns an error or silently truncates the input, which causes downstream JSON parsing failures in the generation pipeline.

Chunked mode solves this by:

- Splitting chunkable payload sections into token-budgeted chunks with configurable overlap.
- Running a narrow extraction task per chunk (map) that produces compact structured output.
- Merging map outputs and running a single synthesis call (reduce) to produce the final manifest.

## Architecture

```
┌──────────────────────────────────────────────┐
│         LLMGenerationLayer (flag on)         │
│                                              │
│  payload_sections = [README, project_info]   │
└──────────────────┬───────────────────────────┘
                   │  LLMStructuredRequest
                   ▼
┌──────────────────────────────────────────────┐
│   LLMService.generate_with_chunked_payload   │
│                                              │
│   1. split_text_into_chunks(chunkable secs)  │
│   2. MAP: generate per chunk → validate      │
│           → repair (1 attempt) → cache       │
│   3. REDUCE: merge map outputs → generate    │
│              → validate → repair (1 attempt) │
└──────────────────────────────────────────────┘
```

**Core modules:**

| Module | Role |
|--------|------|
| `src/core/llm/chunking.py` | `split_text_into_chunks`, `build_token_budget`, `TextChunk`, `ChunkingConfig` |
| `src/core/llm/models/requests.py` | `LLMStructuredRequest`, `LLMPayloadSection`, `LLMTraceContext` |
| `src/core/llm/service.py` | `generate_with_chunked_payload`, map-reduce orchestration, cache helpers |
| `src/core/generation/layers/llm.py` | Feature-flag wiring; calls chunked path when `chunked_mode_enabled` |

## Auto-detection (default behavior)

Chunked mode is **on by default when needed**. The LLM layer estimates the token count of each prompt before issuing a request and automatically routes to the map-reduce path when the estimate exceeds `chunk_max_tokens`. No explicit configuration is required.

**Decision logic (evaluated per request):**

1. If `chunked_mode_enabled = True` → always use chunked mode (force on).
2. If `chunked_mode_enabled = False` → never use chunked mode (force off).
3. If `chunked_mode_enabled` is absent (default) → compare estimated prompt tokens to `chunk_max_tokens`; use chunked mode only when the prompt exceeds the threshold.

The token estimator uses a conservative character-to-token heuristic (`len(text) / 4`) that requires no external dependencies. Because it is intentionally conservative, it will err toward triggering chunking slightly earlier than a precise tokenizer would — which is the safe direction.

## Configuring chunked mode

### Python API

```python
from src.core.generation.models import LayerConfig

# Default: auto-detect based on prompt size
config = LayerConfig(
    use_llm=True,
    llm_config={
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "max_tokens": 8000,
        "temperature": 0.1,
        "timeout": 120,
        # Tune the auto-detect threshold and overlap (optional)
        "chunk_max_tokens": 4000,
        "chunk_overlap_tokens": 256,
    }
)

# Force chunking on regardless of prompt size
config_force_on = LayerConfig(
    use_llm=True,
    llm_config={
        "chunked_mode_enabled": True,
        "chunk_max_tokens": 4000,
        "chunk_overlap_tokens": 256,
    }
)

# Disable chunking entirely (legacy / debugging)
config_force_off = LayerConfig(
    use_llm=True,
    llm_config={
        "chunked_mode_enabled": False,
    }
)
```

### `generate_manifest_for_repository`

```python
from src.core.generation.dataset_generation import generate_manifest_for_repository

# Auto-detect (default): chunking engages automatically for large repos
manifest = await generate_manifest_for_repository(
    repo_url="https://github.com/example/project",
    use_llm=True,
)

# Override threshold (optional)
manifest = await generate_manifest_for_repository(
    repo_url="https://github.com/example/project",
    use_llm=True,
    llm_chunk_max_tokens=4000,
    llm_chunk_overlap_tokens=256,
)

# Force chunking on regardless of size
manifest = await generate_manifest_for_repository(
    repo_url="https://github.com/example/project",
    use_llm=True,
    llm_chunked_mode_enabled=True,
)
```

### Batch script

```bash
conda activate supply-graph-ai

# Default: auto-detects chunking need per repository
python scripts/okh_generation_batch.py \
  --repos-file tests/data/okh_generation/repositories.json \
  --output tests/data/okh_generation/last_batch_report.json \
  --use-llm

# Force chunking on for all repositories
python scripts/okh_generation_batch.py \
  --repos-file tests/data/okh_generation/repositories.json \
  --output tests/data/okh_generation/last_batch_report.json \
  --use-llm \
  --llm-chunked-mode \
  --llm-chunk-max-tokens 4000 \
  --llm-chunk-overlap-tokens 256
```

## Configuration reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `chunked_mode_enabled` | bool or absent | absent (auto) | `True` forces chunking on; `False` forces it off; absent enables auto-detection. |
| `chunk_max_tokens` | int | `4000` | Token budget per chunk, and the threshold for auto-detection: prompts whose estimated token count exceeds this value trigger chunking automatically. |
| `chunk_overlap_tokens` | int | `256` | Token overlap between consecutive chunks. Increase for dense code or tabular content. |

### Inherited parameters (standard LLM layer)

| Parameter | Recommended value (chunked) | Notes |
|-----------|----------------------------|-------|
| `max_tokens` | `8000` | Applies to the reduce call. Map calls use a smaller internal budget. |
| `timeout` | `120` | Chunked jobs are slower; allow extra time per call. |
| `temperature` | `0.1` | Low temperature improves determinism across chunks. |

## Token budgeting

`build_token_budget` computes the available payload space after reserving headroom for:

- `system_tokens` — system/instruction wrapper
- `instruction_tokens` — per-chunk task prompt
- `reserved_output_tokens` — expected completion size per map call
- `safety_margin_tokens` — conservative buffer (default 5% of context window)

If the fixed overhead alone exceeds the context window, the call fails immediately with an explicit error rather than silently truncating.

The default token estimator uses a conservative character-based heuristic (`chars / 4`). A more accurate tokenizer can be substituted by implementing the `TokenEstimator` protocol in `src/core/llm/chunking.py`.

## Caching and checkpointing

Map-stage outputs are cached by an idempotency key derived from:

- Normalized chunk text hash (SHA-256)
- Provider and model name
- Prompt instruction text

On re-runs, cached map results are loaded from disk, skipping the LLM call for that chunk. Only missing or invalid chunks are recomputed, allowing interrupted jobs to resume cleanly.

Cache files are written to a `checkpoint_dir` passed to `generate_with_chunked_payload`. The batch script does not enable caching by default; pass `cache_enabled=True` and a `checkpoint_dir` path when calling the service directly.

## Schema validation and repair

Both map and reduce outputs are validated against Pydantic schemas:

- **Map stage**: a flexible schema accepting any JSON object (used for fact extraction).
- **Reduce stage**: `ChunkedLLMReduceSchema` requiring non-empty `title`, `version`, `function`, and `description` fields.

If validation fails, a single constrained repair prompt is sent to the LLM with the schema definition included. The repair count is recorded in `LLMResponseMetadata`. If the repair still fails, an explicit error response is returned and the reduce stage is skipped.

## Observability

`LLMResponseMetadata` is extended with chunked-mode fields:

| Field | Description |
|-------|-------------|
| `chunk_count` | Total number of chunks processed in the map stage. |
| `map_success_count` | Number of map chunks that produced valid output. |
| `repair_count` | Number of repair attempts triggered (map + reduce combined). |
| `cache_hit_count` | Number of map chunks served from cache. |
| `workflow` | Set to `"chunked_map_reduce"` when chunked mode is active. |

## Quality evaluation

Use `scripts/okh_generation_chunked_evaluation.py` to compare a baseline run against a chunked-mode run:

```bash
# 1. Baseline run (no chunking)
python scripts/okh_generation_batch.py \
  --repos-file tests/data/okh_generation/repositories.json \
  --output tests/data/okh_generation/last_batch_report_baseline.json \
  --use-llm

# 2. Chunked canary run
python scripts/okh_generation_batch.py \
  --repos-file tests/data/okh_generation/repositories.json \
  --output tests/data/okh_generation/last_batch_report_chunked.json \
  --use-llm \
  --llm-chunked-mode

# 3. Evaluate
python scripts/okh_generation_chunked_evaluation.py \
  --baseline tests/data/okh_generation/last_batch_report_baseline.json \
  --candidate tests/data/okh_generation/last_batch_report_chunked.json \
  --output tests/data/okh_generation/chunked_evaluation_report.json
```

### Quality gates

| Gate | Threshold | Description |
|------|-----------|-------------|
| `schema_and_reliability` | error rate increase ≤ 0 | No new errors introduced. |
| `extraction_quality_confidence` | confidence delta ≥ −0.05 | Generation confidence does not regress significantly. |
| `extraction_quality_presence_proxy` | presence delta ≥ −0.05 | Required-field presence does not regress significantly. |
| `efficiency_latency` | latency ratio ≤ 2.5× | Chunked runs may be slower; this bounds the overhead. |

The script exits with code `1` if any gate fails. Thresholds are configurable via CLI flags; see `--help` for details.

## Operational guidance

**When to enable chunked mode:**

- The target repository has a README or file tree likely to exceed ~6 000 tokens.
- You are seeing `"All JSON recovery attempts failed"` errors in LLM mode.
- You need higher coverage of content from large monorepos.

**When to keep chunked mode off:**

- The repository is small and fits comfortably within the context window.
- Latency is a concern (chunked jobs are 1.3–2× slower on average).
- You are running a quick exploratory batch where strict quality is less critical.

**Rollout status (as of 2026-04-03):**

- Auto-detection is the default; chunking engages only when a prompt exceeds `chunk_max_tokens`.
- All four quality gates pass on the 26-repository canary corpus.
- The feature is active and ready for production use.

## Related documentation

- [LLM Service](llm-service.md) — core service API reference
- [LLM Generation Layer](generation.md) — 4-layer generation architecture
- [LLM Configuration](configuration.md) — provider setup and environment variables
- [Batch Testing README](../../tests/data/okh_generation/README.md) — canary run instructions
