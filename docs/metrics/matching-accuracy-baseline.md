# Matching Accuracy Baseline (v1.0.0)

**Date established**: February 2026
**Issue**: 1.2.1 - Establish Matching Accuracy Baseline Metrics
**Ground truth**: 115 labelled requirement-capability pairs

---

## Methodology

### Ground Truth Dataset

The accuracy evaluation uses a manually labelled dataset of 115 requirement-capability pairs stored in `tests/data/matching/ground_truth/matching_ground_truth.json`. Each pair represents a manufacturing process requirement (from an OKH manifest) paired with a facility capability (from an OKW facility), labelled as either a true match or a true non-match.

| Category | Count | Description |
|----------|-------|-------------|
| `process_true_positive` | 20 | Process requirements that should match capabilities |
| `process_true_negative` | 20 | Process requirements that should NOT match capabilities |
| `synonym_match` | 15 | Semantically equivalent terms (e.g., "welding" vs "Welder") |
| `near_miss` | 10 | Similar but distinct processes (e.g., "brazing" vs "Welder") |
| `uri_normalization` | 5 | Short codes vs URI-formatted capabilities |
| `cross_domain_negative` | 15 | Requirements vs capabilities from different domains |
| `material_match` | 15 | Material requirement vs material capability |
| `edge_case` | 15 | Boundary cases (empty, whitespace, unusual formats) |

**Balance**: 60 expected matches (52.2%) / 55 expected non-matches (47.8%)

### Evaluation Process

For each ground truth pair, the evaluator calls the three internal matching layers of `MatchingService`:

1. **Direct matching** (`_direct_match`): Exact/near-exact string matching with normalization
2. **Heuristic matching** (`_heuristic_match`): Capability-centric rules from `manufacturing.yaml`
3. **NLP matching** (`_nlp_match`): Semantic similarity via spaCy

The combined prediction is `True` if **any** layer returns a match. Confidence is assigned based on which layer matched first (direct=1.0, heuristic=0.8, NLP=0.7, none=0.0).

---

## Baseline Results

### Per-Layer Metrics

| Layer | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |
|-------|-----------|--------|----|----------|----|----|----|-----|
| **Direct** | **0.9500** | 0.6333 | 0.7600 | 0.7913 | 38 | 2 | 53 | 22 |
| **Heuristic** | **1.0000** | 0.1000 | 0.1818 | 0.5304 | 6 | 0 | 55 | 54 |
| **NLP** | 0.8286 | 0.4833 | 0.6105 | 0.6783 | 29 | 6 | 49 | 31 |
| **Combined** | **0.8519** | **0.7667** | **0.8070** | **0.8087** | 46 | 8 | 47 | 14 |

### Key Observations

- **Direct layer** is the workhorse: high precision (95%) catches most matches with very few false positives
- **Heuristic layer** is perfectly precise (100%) but fires rarely (6 matches) — heuristic rules coverage is limited
- **NLP layer** adds meaningful recall (+8 additional true positives) but introduces some false positives (6)
- **Combined system** achieves 80.9% accuracy with good balance between precision (85.2%) and recall (76.7%)

### Per-Category Accuracy (Combined)

| Category | Precision | Recall | F1 | Accuracy |
|----------|-----------|--------|----|----------|
| `cross_domain_negative` | — | — | — | **1.000** |
| `synonym_match` | 1.000 | 0.933 | 0.966 | **0.933** |
| `process_true_negative` | — | — | — | **0.900** |
| `uri_normalization` | 1.000 | 0.800 | 0.889 | 0.800 |
| `edge_case` | 0.818 | 0.900 | 0.857 | 0.800 |
| `material_match` | 0.875 | 0.700 | 0.778 | 0.733 |
| `near_miss` | — | — | — | 0.700 |
| `process_true_positive` | 1.000 | 0.600 | 0.750 | **0.600** |

**Strongest areas**: Cross-domain negatives (100%), synonym matching (93.3%), process negatives (90%)

**Weakest areas**: Process true positives (60%), near-miss discrimination (70%), material matching (73.3%)

---

## Identified Weaknesses

### 1. Missing Semantic Relationships (8 cases)

The system fails to recognise that certain TSDC codes map to specific equipment:

- **PCB** → Pick_and_place, Reflow_oven (2 misses)
- **SMT** → Pick_and_place, Reflow_oven (2 misses)
- **Post-processing** → Deburring, Anodizing, Painting (4 misses)

**Root cause**: No heuristic rules mapping TSDC codes to the specific equipment required for those processes. These require new capability rules in `manufacturing.yaml`.

### 2. NLP False Positives (6 cases)

The NLP layer incorrectly matches some semantically similar but functionally different processes:

- "3DP" vs CNC_mill, "PCB" vs CNC_mill (manufacturing similarity)
- "cnc plasma cutting" vs CNC_mill (substring similarity)
- "electroplating" vs Anodizing_line, "brazing" vs Welder (surface treatment / joining confusion)
- "Aluminum 6061-T6" vs Aluminum_7075 (different alloys)

**Root cause**: spaCy's word vectors treat manufacturing terms as semantically close. Domain-specific constraints could help.

### 3. Material Full-Name ↔ Abbreviation (3 cases)

- "Thermoplastic Polyurethane" vs TPU
- "Polylactic Acid" vs PLA
- "Acrylic Sheet" vs Plastic

**Root cause**: No abbreviation-expansion rules in the matching pipeline.

### 4. Edge Case: Empty String Matching (2 cases)

- "3DP" vs "" and "" vs "" both return `True` from the direct matcher

**Root cause**: Normalization reduces both to empty strings, which then match as equal.

---

## Confidence Calibration

| Confidence Bucket | Count | Actual Positive Rate | Mean Confidence |
|-------------------|-------|---------------------|-----------------|
| [0.0, 0.2) | 61 | 0.23 | 0.00 |
| [0.2, 0.4) | 0 | — | — |
| [0.4, 0.6) | 0 | — | — |
| [0.6, 0.8) | 14 | 0.57 | 0.70 |
| [0.8, 1.0] | 40 | 0.95 | 1.00 |

**Interpretation**: High-confidence predictions (0.8-1.0) are very reliable (95% actually positive). The NLP-confidence bucket (0.6-0.8) is only 57% reliable — these predictions need more scrutiny. The system is well-calibrated at the extremes but has a gap in the middle range.

### Threshold Recommendations

| Use Case | Recommended Threshold | Expected Precision | Expected Recall |
|----------|----------------------|-------------------|-----------------|
| **High-confidence only** | ≥ 0.8 | ~95% | ~63% |
| **Balanced** | ≥ 0.7 | ~85% | ~77% |
| **High-recall** | ≥ 0.0 (all) | ~85% | ~77% |

---

## LLM Layer Results (4-Layer System)

**Date**: February 2026

### Per-Configuration Comparison

| Config | Precision | Recall | F1 | Accuracy | Key Insight |
|--------|-----------|--------|----|----------|-------------|
| **3-Layer Baseline** | 0.8519 | 0.7667 | **0.8070** | 0.8087 | Strong without any LLM |
| **+ Sonnet 4.5** | 0.8254 | 0.8667 | **0.8455** | 0.8348 | +4% F1, mostly recall improvement |
| **+ Opus 4.6** | 0.8095 | 0.8500 | **0.8293** | 0.8174 | Diminishing returns over Sonnet |
| **+ llama3.2:3b** | 0.5263 | 1.0000 | **0.6897** | 0.5304 | "Yes bot" -- too small to reason |

### LLM-Only Metrics

| Model | Precision | Recall | F1 | Key Insight |
|-------|-----------|--------|----|-------------|
| Sonnet 4.5 | 0.8723 | 0.6833 | 0.7664 | Good precision, moderate recall |
| Opus 4.6 | 0.8936 | 0.7000 | 0.7850 | Slightly better precision |
| llama3.2:3b | 0.5225 | 0.9667 | 0.6784 | Says "yes" to everything |

### Key Findings

1. **The 3-layer system provides the majority of quality** -- the LLM layer adds ~4% F1 with Sonnet 4.5
2. **Diminishing returns above Sonnet 4.5** -- Opus 4.6 (more expensive) performs slightly worse in the 4-layer combined system
3. **Very small models (3B) are harmful** -- they act as "yes bots" and degrade precision from 85% to 53%
4. **The optimization target** is the gap between 3B (useless) and Sonnet 4.5 (good)

### Mismatch Pattern Analysis

A detailed analysis of failure patterns is available in `docs/metrics/mismatch-analysis.md`. Summary:

| Category | Cases | Type | Impact |
|----------|-------|------|--------|
| Process-Requires-Sub-Process | 8 | FN | PCB/SMT -> equipment, Post-processing -> finishing |
| NLP Semantic Over-Matching | 5 | FP | Similar but different manufacturing processes |
| Abbreviation/URI Resolution | 4 | FN | TPU/PLA/SLA abbreviations, URI slugs |
| Material Confusion | 2 | Mixed | Material hierarchy and alloy distinctions |
| Empty String Edge Cases | 2 | FP | Direct layer doesn't guard empty strings |

Fixing the top 3 categories would resolve **17 of 22 mismatches** (77%).

---

## Improvement Roadmap

| Priority | Improvement | Expected Impact |
|----------|------------|----------------|
| **High** | Add heuristic rules for PCB/SMT ↔ equipment mapping | +4-6 recall points |
| **High** | Add heuristic rules for Post-processing ↔ finishing equipment | +4-6 recall points |
| **Medium** | Add material abbreviation expansion (TPU, PLA, ABS, PETG) | +2-3 recall points |
| **Medium** | Fix empty-string matching bug in direct layer | +2 precision points |
| **Medium** | Explore mid-tier local models (7B-14B) for LLM layer | Local LLM with competitive quality |
| **Low** | Tighten NLP threshold or add negative rules for near-miss cases | +3-5 precision points |
| **Low** | Add "stereolithography" ↔ SLA synonym mapping | +1 recall point |

**Target after improvements**: Combined accuracy > 90%, F1 > 0.88

---

## Running the Accuracy Tests

```bash
# Run 3-layer accuracy evaluation
conda activate supply-graph-ai
pytest tests/e2e/test_matching_accuracy.py -v -s

# Run LLM accuracy evaluation (requires ANTHROPIC_API_KEY and/or Ollama)
pytest tests/e2e/test_matching_accuracy_llm.py -v -s

# Run model ladder (benchmark multiple local models)
pytest tests/e2e/test_model_ladder.py -v -s

# Regenerate the baseline report
python -c "
import asyncio, json
from tests.benchmarks.conftest import _ensure_domains_registered
from src.core.services.matching_service import MatchingService
from tests.data.matching.accuracy_evaluator import MatchingAccuracyEvaluator, load_ground_truth

async def main():
    _ensure_domains_registered()
    MatchingService._instance = None
    s = MatchingService()
    await s.initialize(None, None)
    e = MatchingAccuracyEvaluator(s)
    cases = load_ground_truth()
    preds = await e.evaluate_all(cases)
    report = e.generate_report(preds, cases)
    e.print_report(report)
    with open('tests/data/matching/ground_truth/baseline_accuracy_report.json', 'w') as f:
        json.dump(report, f, indent=2)

asyncio.run(main())
"
```

---

## File Reference

| File | Purpose |
|------|---------|
| `tests/data/matching/ground_truth/matching_ground_truth.json` | 115 labelled test cases |
| `tests/data/matching/ground_truth/baseline_accuracy_report.json` | Baseline measurement results |
| `tests/data/matching/ground_truth/llm_anthropic_default_accuracy_report.json` | Sonnet 4.5 LLM results |
| `tests/data/matching/ground_truth/llm_anthropic_frontier_accuracy_report.json` | Opus 4.6 LLM results |
| `tests/data/matching/ground_truth/llm_ollama_small_accuracy_report.json` | Ollama 3B LLM results |
| `tests/data/matching/ground_truth/model_ladder_summary.json` | Model ladder comparison |
| `tests/data/matching/accuracy_evaluator.py` | Evaluation framework (3-layer + LLM) |
| `tests/e2e/test_matching_accuracy.py` | 3-layer accuracy test suite (15 tests) |
| `tests/e2e/test_matching_accuracy_llm.py` | LLM accuracy test suite (16 tests) |
| `tests/e2e/test_model_ladder.py` | Model ladder benchmark (parameterized) |
| `tests/data/generation/generation_evaluator.py` | Generation quality evaluator |
| `tests/data/generation/ground_truth/generation_ground_truth.json` | Generation ground truth dataset |
| `docs/metrics/matching-accuracy-baseline.md` | This document |
| `docs/metrics/mismatch-analysis.md` | Detailed mismatch pattern analysis |
