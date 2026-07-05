# LLM Matching Layer

**Related**: [Matching overview](index.md) · [NLP Matching](nlp-matching.md) · [Match Explanation](match-explanation.md)

The LLM Matching layer is Layer 4 in OHM's 4-layer matching architecture. Where the earlier layers rely on exact strings, rules, or word-vector similarity, the LLM layer sends a richly-contextualised prompt to a Large Language Model and asks it to reason about whether a facility *can actually produce* a required item — even when terminology is non-standard, information is incomplete, or substitutions are needed.

## When it runs

The LLM layer is **opt-in per request**. It does not run automatically on every match because it carries a non-trivial latency and API cost. Enable it with:

- **API**: include `"use_llm": true` in the request body
- **CLI**: pass `--use-llm` to `ohm match requirements`

```bash
ohm match requirements my-design.okh.json --use-llm
ohm match requirements my-design.okh.json --use-llm --llm-provider anthropic --llm-model claude-3-5-haiku-20241022
```

When `use_llm` is false (the default), the matching pipeline stops after Layer 3 (NLP). When it is true, any requirement that reached Layer 4 without a conclusive match is submitted to the LLM.

## What the layer analyses

Each requirement–capability pair is evaluated across five dimensions:

| Dimension | What it asks |
|---|---|
| **Process compatibility** | Can the facility perform the required manufacturing process, or a recognised substitute? |
| **Material availability** | Does the facility have the required material, or a functionally equivalent alternative? |
| **Tool / equipment** | Does the facility have the necessary equipment, or an adaptation that achieves the same result? |
| **Expertise / skills** | Does the facility have the required technical skills, including transferable skills? |
| **Scale / capacity** | Can the facility produce at the required quantity — or adapt (e.g. batch runs)? |

Each dimension receives an individual score (0.0–1.0). The layer also produces an overall `confidence_score` and a `match_decision` boolean.

## Confidence thresholds

| Range | Interpretation |
|---|---|
| 0.9 – 1.0 | Excellent — facility clearly has all required capabilities |
| 0.7 – 0.9 | Good — facility has most capabilities with minor gaps |
| 0.5 – 0.7 | Moderate — facility has some capabilities but significant gaps |
| 0.3 – 0.5 | Poor — facility has limited relevant capabilities |
| 0.0 – 0.3 | No match |

## Taxonomy-informed prompting

Before the LLM sees the requirement and capability strings, the layer enriches the prompt with knowledge drawn from OHM's process taxonomy (`src/core/taxonomy`):

- The canonical name and definition of both the requirement and capability (if they are known processes)
- Their parent category and sub-processes in the taxonomy hierarchy
- Whether they are related in the taxonomy tree
- Hard-coded process–equipment relationships (e.g. PCB fabrication requires pick-and-place machines and reflow ovens)
- Common abbreviation expansions (SLA, FDM, SMT, TPU, PLA, ABS, CNC, …)
- Critical negative examples to prevent common confusions (brazing ≠ welding, electroplating ≠ anodizing, …)

This means the LLM is not asked to guess domain knowledge from scratch — it is given a structured briefing that reflects OHM's own model of the manufacturing world.

## Crisis response context

The system prompt frames every analysis as a *crisis response scenario*. The practical effect is that the LLM is instructed to:

- Treat non-standard or informal terminology charitably rather than literally
- Actively look for substitutions (material, process, equipment)
- Work with partial or uncertain facility descriptions
- Prioritise practical outcomes over terminology precision

This framing was chosen because OHM is designed for real-world maker networks where facility descriptions vary widely and an overly strict matcher would produce false negatives.

## Implementation details

### Class

```python
# src/core/matching/llm_matcher.py
class LLMMatcher(BaseMatchingLayer):
    def __init__(
        self,
        domain: str = "general",
        llm_service: Optional[Any] = None,
        preserve_context: bool = False,
    ): ...
```

`LLMMatcher` inherits `BaseMatchingLayer` (like every other layer) and is registered as `MatchingLayer.LLM`.

### LLM service configuration

The layer creates its own `LLMService` instance on first use:

| Parameter | Value |
|---|---|
| Default provider | Anthropic |
| Default model | Taken from centralised `LLMConfig` (not hard-coded) |
| Temperature | 0.2 (low, for consistent JSON output) |
| Max tokens | 2000 |
| Timeout | 30 s |
| Max retries | 3 |

### Match flow

```
for each (requirement, capability) pair:
    1. Build prompt  ← system prompt + taxonomy context + domain context
    2. Call LLM service
    3. Extract JSON from response
    4. Validate required fields (match_decision, confidence_score, capability_assessment)
    5. Map to MatchingResult
    6. (Optionally) write debug context file
```

### Response parsing

The LLM is instructed to return a structured JSON object. The parser extracts the first complete `{…}` block from the response and validates that `match_decision`, `confidence_score`, and `capability_assessment` are present. If parsing fails, the layer returns a no-match result and logs the error rather than raising an exception.

### Debug context files

Pass `preserve_context=True` when constructing `LLMMatcher` (or set via the relevant service config) to retain per-analysis Markdown files under `temp_matching_context/`. Each file records the full prompt and LLM response for that pair. Files are deleted after the analysis completes by default.

## Domain support

Domain-specific substitution tables are injected into every prompt:

| Domain | Examples provided |
|---|---|
| `manufacturing` | CNC ↔ manual machining, 316L ↔ 304 stainless, laser ↔ plasma cutting, mass ↔ batch production |
| `cooking` | Sauté ↔ pan-fry, oven ↔ toaster oven, fresh ↔ dried herbs |
| `general` | Generic process/material/equipment substitution guidance |

## API response fields

When `use_llm` is true the match response includes:

```json
{
  "matching_metrics": {
    "direct_matches": 1,
    "heuristic_matches": 2,
    "nlp_matches": 1,
    "llm_matches": 1
  },
  "llm_used": true
}
```

`llm_matches` counts solutions where the final match was resolved at Layer 4.

## CLI usage

```bash
# Enable LLM layer with default provider from config
ohm match requirements my-design.okh.json --use-llm

# Override provider and model
ohm match requirements my-design.okh.json \
  --use-llm \
  --llm-provider anthropic \
  --llm-model claude-3-5-haiku-20241022

# Combine with --explain to see which layer resolved each match
ohm match requirements my-design.okh.json --use-llm --explain
```

## Configuration

LLM provider credentials and the default model are managed through OHM's centralised LLM configuration (see `src/core/config/llm.py` and `docs/development/llm-configuration.md`). The matching layer reads from that config automatically; no extra setup is needed beyond configuring the provider credentials.

## Limitations

- **Latency**: An LLM call adds hundreds of milliseconds to seconds per requirement–capability pair. For large facility pools, this multiplies. Consider using it selectively (e.g., only when the first three layers return no match).
- **Cost**: Each call consumes LLM API tokens. High-volume matching should be budgeted accordingly.
- **Non-determinism**: Temperature 0.2 keeps output stable, but the LLM is not guaranteed to return identical results for identical inputs.
- **Language**: The system prompt and taxonomy context are English-only.
- **JSON robustness**: If the LLM returns malformed JSON, the layer falls back to a no-match result rather than propagating an error upward.
