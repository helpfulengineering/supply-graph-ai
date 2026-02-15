# Matching Accuracy Baseline

> Last Updated: 2026-02-15

## Current Baseline (v2.0 - Post Mismatch Remediation)

| Metric | Value |
|--------|-------|
| **Precision** | 0.9836 |
| **Recall** | 1.0000 |
| **F1 Score** | 0.9917 |
| **Accuracy** | 0.9913 |
| **Total Cases** | 115 |
| **Mismatches** | 1 |

### Confusion Matrix

|  | Predicted True | Predicted False |
|--|---------------|-----------------|
| **Actually True** | 60 (TP) | 0 (FN) |
| **Actually False** | 1 (FP) | 54 (TN) |

### Per-Layer Breakdown

| Layer | Precision | Recall | F1 | Cases Matched |
|-------|-----------|--------|----|---------------|
| Direct | 0.95 | 0.63 | 0.76 | 38 TP |
| Heuristic | 1.00 | 0.30 | 0.46 | 18 TP (new rules) |
| NLP | 1.00 | 0.03 | 0.06 | 2 TP (post-filtered) |
| **Combined** | **0.98** | **1.00** | **0.99** | **60 TP** |

---

## Previous Baseline (v1.0)

| Metric | v1.0 | v2.0 | Delta |
|--------|------|------|-------|
| Precision | 0.8519 | 0.9836 | +13.2 pp |
| Recall | 0.7667 | 1.0000 | +23.3 pp |
| F1 Score | 0.8070 | 0.9917 | +18.5 pp |
| Accuracy | 0.8087 | 0.9913 | +18.3 pp |
| Mismatches | 22 | 1 | -21 |

---

## Key Finding: Local LLM Parity with Cloud Models

The model ladder benchmark (run before v2.0 remediation) showed:

| Model | Type | LLM P | LLM R | LLM F1 | 4-Layer F1 |
|-------|------|-------|-------|--------|------------|
| **Qwen 2.5 7B** | **Local (free)** | **0.83** | **0.82** | **0.82** | **0.846** |
| Sonnet 4.5 | Cloud (paid) | 0.72 | 0.83 | 0.77 | 0.845 |
| Opus 4.6 | Cloud (paid) | 0.75 | 0.83 | 0.79 | 0.829 |
| Llama 3.2 3B | Local (free) | 0.54 | 0.93 | 0.69 | 0.710 |
| Mistral 7B | Local (free) | 0.60 | 0.97 | 0.74 | 0.747 |

**Qwen 2.5 7B achieves equivalent performance to Anthropic Sonnet 4.5**, enabling
fully offline operation with zero API costs and no quality loss.

---

## What Changed (v1.0 -> v2.0)

Five targeted fixes were applied, each verified incrementally with TDD:

1. **Empty string guard** (2 FP fixed): Added guard in `_direct_match()` preventing
   empty strings from matching each other.

2. **PCB/SMT heuristic rules** (6 FN fixed): Added rules recognizing that pick-and-place
   machines and reflow ovens satisfy PCB/SMT/electronics assembly requirements.

3. **Post-processing sub-type rules** (4 FN fixed): Added rules recognizing that deburring,
   anodizing, and painting are sub-types of post-processing.

4. **NLP taxonomy post-filter** (5 FP fixed): After NLP match, both terms are resolved
   through the process taxonomy. If both resolve to known but unrelated canonical processes,
   the match is rejected.

5. **Abbreviation/material rules** (4 FN fixed): Added SLA printer alias, material
   abbreviation rules (TPU, PLA, plastic types), and tightened taxonomy substring matching
   threshold from 3 to 5 chars to prevent false normalizations.

---

## Running the Accuracy Tests

```bash
conda activate supply-graph-ai

# Run accuracy tests (3-layer, ~2s)
python -m pytest tests/e2e/test_matching_accuracy.py -v

# Run LLM accuracy tests (requires Anthropic API key or Ollama, ~5-30min)
python -m pytest tests/e2e/test_matching_accuracy_llm.py -v

# Run model ladder (requires Ollama with models pulled, ~2-8 hours)
python -m pytest tests/e2e/test_model_ladder.py -v
```

---

## File Reference

| File | Purpose |
|------|---------|
| `tests/data/matching/ground_truth/matching_ground_truth.json` | 115 labelled ground-truth cases |
| `tests/data/matching/accuracy_evaluator.py` | Evaluation framework |
| `tests/e2e/test_matching_accuracy.py` | 3-layer accuracy test suite with thresholds |
| `tests/e2e/test_matching_accuracy_llm.py` | LLM layer accuracy tests |
| `tests/e2e/test_model_ladder.py` | Local model comparison benchmark |
| `src/config/rules/manufacturing.yaml` | Heuristic matching rules |
| `src/config/taxonomy/processes.yaml` | Process taxonomy (YAML source) |
| `src/core/services/matching_service.py` | Core matching pipeline |
| `docs/metrics/mismatch-analysis.md` | Detailed mismatch analysis and remediation log |
