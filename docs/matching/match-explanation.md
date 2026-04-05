# Match Explanation (Transparency)

**Related**: Issue 1.2.4 · [Matching overview](index.md) · [Rule design](../development/rule_design.md)

When matching requirements to facilities, you can request **per-facility explanations** that describe why a facility matched or did not match, which layer (direct, heuristic, NLP, LLM) was used, and which rule (if any) applied.

## How to request explanations

- **API**: Send `include_explanation: true` in the match request body. Each solution in the response will include `explanation` (structured) and `explanation_human` (text).
- **CLI**: Use the `--explain` flag:
  ```bash
  ohm match requirements my-design.okh.json --explain
  ```
  In current CLI behavior, `--verbose` also enables explanation output automatically for `match requirements`.
  Explanations are printed under each facility in table output; in JSON output they appear as `explanation` and `explanation_human` on each solution.

### Manual testing with synthetic data (no server/storage)

If you run the CLI without a running API server or with empty facility storage, you will see “No matching facilities found” because the default is to load facilities from storage. To test matching and `--explain` using the repo’s synthetic OKH/OKW data, pass **`--facility-file`** with a local OKW JSON file (single facility object or a JSON array of facilities). The CLI will use that file instead of storage (and will use the direct matching path).

**Example – one facility, one OKH, with explanations (works out of the box):**

```bash
ohm match requirements synthetic_data/laser-cut-acrylic-display-case-2-3-3-okh.json \
  --facility-file synthetic_data/laser-fabrication-lab-005-okw.json \
  --explain
```

**Example – multiple facilities from one JSON array:**  
Create a file (e.g. `synthetic_data/facility-pool.json`) that is a JSON array of OKW facility objects, or use a single facility file as above.

| OKH (design) | OKW (facility) that can match |
|-------------|--------------------------------|
| `synthetic_data/laser-cut-acrylic-display-case-2-3-3-okh.json` | `synthetic_data/laser-fabrication-lab-005-okw.json` (LASER + Assembly) |
| `synthetic_data/3d-printed-prosthetic-hand-1-5-5-okh.json` | `synthetic_data/rapid-prototyping-lab-001-okw.json` (3DP; OKH also lists Post-processing, Assembly — facility must satisfy all) |
| `synthetic_data/cnc-machined-aluminum-bracket-2-7-3-okh.json` | `synthetic_data/full-service-cnc-shop-002-okw.json` or `professional-machine-shop-*.okw.json` |
| `synthetic_data/arduino-based-iot-sensor-node-2-1-0-okh.json` | `synthetic_data/electronics-assembly-house-*.okw.json` |

See `docs/testing/workflows/README.md` and `synthetic_data/` for the full list of synthetic OKH and OKW files.

## Explanation format

### Structured (`explanation`)

- **facility_id**, **facility_name**: Identifiers for the facility.
- **overall_status**: `"matched"` or `"not_matched"`.
- **overall_confidence**: 0.0–1.0.
- **requirement_matches**: List of per-requirement details:
  - **requirement_value**: The requirement text.
  - **status**: `"matched"` or `"not_matched"`.
  - **confidence**: Score for this requirement.
  - **matched_capability**: Capability that satisfied the requirement (if matched).
  - **matching_layer**: `"direct"`, `"heuristic"`, `"nlp"`, or `"llm"`.
  - **rule_id**: Rule that fired (e.g. heuristic rule ID from manufacturing rules).
  - **explanation**: Short text for this requirement.
- **why_matched**: Summary of why the facility matched (when overall matched).
- **why_not_matched**: Summary of why it did not match (when overall not matched).
- **matching_layers_used**: List of layer names that contributed.
- **missing_capabilities**: Capabilities that were required but not found (when not matched).

### Human-readable (`explanation_human`)

A single string suitable for logs or CLI:

- For **matched** facilities: facility name, confidence, “Why this facility matches”, and a requirement breakdown (each requirement, layer, matched capability, optional rule ID).
- For **not matched**: facility name, “Why this facility doesn’t match”, and missing/unmatched details.

## Matching layers

| Layer      | Meaning |
|-----------|--------|
| **direct**  | Exact or near-exact string match (normalized). |
| **heuristic** | Rule-based match from capability rules (e.g. `manufacturing.yaml`); **rule_id** is set when a rule fires. |
| **nlp**      | Semantic similarity (e.g. spaCy); no rule_id. |
| **llm**      | LLM-based match (when enabled). |

## Implementation notes

- **Model**: `src/core/models/match_explanation.py` — `MatchExplanation`, `RequirementMatchDetail`, `MatchLayer`, `MatchStatus`.
- **Service**: `MatchingService.get_match_explanation(requirements, capabilities, facility_id, facility_name, domain)`.
- **API**: Manufacturing match route adds `explanation` and `explanation_human` to each result when `include_explanation` is true.
- **CLI**: Fallback (direct service) path attaches explanations via `_attach_explanations_to_solutions` when `--explain` is used.

Explanations are currently supported for the **manufacturing** domain; cooking and other domains do not yet populate explanations.
