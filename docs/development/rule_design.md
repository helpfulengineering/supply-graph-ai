# Heuristic Rule Design Guidelines

This document describes how to add and refine capability-centric heuristic rules used by the matching service (Layer 2). Rules are defined in YAML and loaded from **`src/config/rules/manufacturing.yaml`** at runtime (see `CapabilityRuleManager`).

## Rule format

Each rule is **capability-centric**: it states which **requirements** a given **capability** can satisfy.

```yaml
  rule_id:
    id: "rule_id"
    type: "capability_match"
    capability: "normalized capability string"   # e.g. "pick and place", "cnc mill"
    satisfies_requirements: ["req1", "req2", …]  # requirement strings this capability can satisfy
    confidence: 0.9
    domain: "manufacturing"
    description: "Short explanation"
    source: "Optional reference"
    tags: ["tag1", "tag2"]
```

- **`capability`**: The facility-side process/capability, **after normalization**. Use lowercase, spaces (not underscores) for multi-word names. This is matched against the normalized capability from the ground truth or API (e.g. Wikipedia URIs become "pick and place").
- **`satisfies_requirements`**: List of requirement strings that this capability is allowed to satisfy. Include:
  - Canonical taxonomy IDs (e.g. `pcb_fabrication`, `post_processing`) when the requirement is normalized via the process taxonomy.
  - Common phrasings and abbreviations (e.g. `pcb`, `smt`, `post-processing`, `post processing`).

Matching is **exact** on the normalized strings: the requirement (normalized) must equal one of the entries in `satisfies_requirements`, and the capability (normalized) must equal `capability`.

## Normalization

Before heuristic matching, both requirement and capability are normalized by `MatchingService._normalize_process_name()`:

- Process taxonomy: many terms map to canonical IDs (e.g. `PCB` → `pcb_fabrication`, `Post-processing` → `post_processing`).
- Wikipedia URIs: the slug is extracted and normalized (e.g. `Pick_and_place` → `pick and place`).
- So rules should use **normalized** forms: e.g. capability `"pick and place"`, and in `satisfies_requirements` include both `pcb_fabrication` and `pcb` if both can appear.

## When to add a new rule vs extend an existing one

- **Add a new rule** when you are defining a **new capability** (e.g. a new piece of equipment or process) and which requirements it can satisfy. Example: adding `reflow_oven_capability` for reflow ovens.
- **Extend an existing rule** when the **same capability** should also satisfy additional requirement phrasings or taxonomy IDs. Add those strings to `satisfies_requirements` of the existing rule. Example: adding `"pcb fabrication"` and `"pcb_fabrication"` to `pick_and_place_capability`.

## Confidence and threshold

- **Rule confidence**: Use `0.85`–`0.95` for well-established mappings; `0.7`–`0.85` for broader or less precise ones.
- **Match threshold**: The matching layer only accepts a heuristic match if `result.confidence >= 0.7`. Rules with confidence below 0.7 are effectively unused.

## Validation

1. **Accuracy**: After changing rules, run the matching accuracy suite:
   ```bash
   pytest tests/e2e/test_matching_accuracy.py -v
   ```
2. **Rule performance**: Run the heuristic rule analyzer to see which rules fire and their precision:
   ```bash
   python -m tests.data.matching.heuristic_rule_analyzer --markdown docs/metrics/heuristic_rule_performance.md --json docs/metrics/heuristic_rule_performance.json
   ```
3. **No regressions**: Ensure combined accuracy and per-layer thresholds in `tests/e2e/test_matching_accuracy.py` still pass.

## Performance report

The latest per-rule hit counts and precision are in:
- **Markdown**: [docs/metrics/heuristic_rule_performance.md](../metrics/heuristic_rule_performance.md)
- **JSON**: `docs/metrics/heuristic_rule_performance.json`

Rules that "never triggered" in the report just mean no ground-truth case (in the current 115-case set) had that capability/requirement combination after direct match was skipped; they are not necessarily bad rules.

## Examples

**Equipment satisfying a high-level requirement (process → sub-equipment):**

```yaml
  pick_and_place_capability:
    capability: "pick and place"
    satisfies_requirements: ["pcb", "pcb_fabrication", "pcb fabrication", "smt", "surface mount technology", "electronics assembly"]
    confidence: 0.9
```

**Post-processing sub-type:**

```yaml
  deburring_capability:
    capability: "deburring"
    satisfies_requirements: ["post-processing", "post processing", "post_processing", "finishing", "deburring"]
    confidence: 0.85
```

**Material abbreviation:**

```yaml
  pla_material_capability:
    capability: "pla"
    satisfies_requirements: ["polylactic acid", "pla", "pla filament", "bioplastic"]
    confidence: 0.95
```

## Related

- [Matching accuracy baseline](../metrics/matching-accuracy-baseline.md)
- [Mismatch analysis](../metrics/mismatch-analysis.md)
- `src/core/matching/capability_rules.py` — rule loading and `CapabilityMatcher`
