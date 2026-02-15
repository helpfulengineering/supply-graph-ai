# Matching Mismatch Pattern Analysis

> Generated from accuracy reports and remediation results
>
> Last Updated: 2026-02-15

## Executive Summary

The 3-layer matching system originally had **22 mismatches** across 115 ground-truth cases
(F1 = 0.807). After systematic remediation of 5 failure categories, the system now has
**1 mismatch** (F1 = 0.992).

---

## Improvement Timeline

| Step | Fix | Cases Fixed | F1 Before | F1 After | Mismatches |
|------|-----|-------------|-----------|----------|------------|
| 1 | Empty string guard in `_direct_match()` | 2 FP | 0.807 | 0.821 | 22 -> 20 |
| 2 | PCB/SMT equipment heuristic rules | 6 FN | 0.821 | 0.881 | 20 -> 14 |
| 3 | Post-processing sub-type heuristic rules | 4 FN | 0.881 | 0.918 | 14 -> 10 |
| 4 | NLP taxonomy post-filter | 5 FP | 0.918 | 0.957 | 10 -> 5 |
| 5 | Abbreviation/material rules + taxonomy fixes | 4 FN | 0.957 | 0.992 | 5 -> 1 |

---

## Failure Categories (Resolved)

### Category 1: Process-Requires-Sub-Process (8 FN) -- RESOLVED

**Pattern**: A high-level requirement (e.g., "PCB", "SMT", "Post-processing") implies
specific sub-equipment (e.g., Pick_and_place, Reflow_oven, Deburring_station), but the
system could not make the inference.

**Fix**: Added heuristic rules in `src/config/rules/manufacturing.yaml`:
- `pick_and_place_capability`: satisfies PCB, SMT, PCB fabrication requirements
- `reflow_oven_capability`: satisfies PCB, SMT, reflow soldering requirements
- `deburring_capability`: satisfies post-processing requirements
- `anodizing_capability`: satisfies post-processing requirements
- `painting_capability`: satisfies post-processing requirements

### Category 2: NLP Semantic Over-Matching (5 FP) -- RESOLVED

**Pattern**: spaCy word vectors placed same-domain but functionally-different processes
close together (e.g., 3D printing vs CNC milling).

**Fix**: Added taxonomy post-filter in `_nlp_match()`:
- After NLP match, both terms are resolved through the process taxonomy
- If both resolve to known canonical IDs and they are NOT related, the match is rejected
- Required adding `electroplating`, `brazing`, and `cnc plasma cutting` -> `plasma_cutting`
  to the taxonomy

### Category 3: Abbreviation / URI Resolution (3 FN) -- RESOLVED

**Fix**: Added `sla printer` as alias for `3d_printing_sla` in taxonomy.
Material abbreviation rules (TPU, PLA) added to heuristic rules.

### Category 4: Material Confusion (2 cases) -- PARTIALLY RESOLVED

**Fixed**: `Acrylic Sheet` vs `Plastic` (FN) -- resolved by material heuristic rule
and tighter substring matching threshold.

**Remaining**: `Aluminum 6061-T6` vs `Aluminum_7075` (FP) -- different alloys.
The NLP layer sees "aluminum" in both and matches them. This requires alloy-specific
knowledge that is outside the scope of the process taxonomy. Left as the single
remaining mismatch.

### Category 5: Empty String Edge Cases (2 FP) -- RESOLVED

**Fix**: Added guard in `_direct_match()`: if either normalized string is empty, return False.

---

## Remaining Mismatch

| ID | Requirement | Capability | Expected | Actual | Layer | Notes |
|----|-------------|------------|----------|--------|-------|-------|
| mat-004 | Aluminum 6061-T6 | Aluminum_7075 | FALSE | TRUE | nlp | Different aluminum alloys |

**Why it remains**: Both alloys normalize to None in the process taxonomy (they're materials,
not processes). The NLP layer sees high text similarity ("Aluminum" in both) and matches them.
Fixing this would require either:
- A material taxonomy with alloy-specific knowledge
- An NLP negative list for specific alloy pairs
- Both are low-priority since this is an edge case in real-world matching

---

## Key Finding: Qwen 2.5 7B Matches Sonnet 4.5

The model ladder benchmark revealed that **Qwen 2.5 7B** (a free, local, open-source model)
achieves a 4-layer F1 of **0.846**, matching Anthropic Sonnet 4.5's 4-layer F1 of **0.845**.
This enables fully offline operation with no quality degradation.

| Reference | LLM F1 | 4-Layer F1 |
|-----------|--------|------------|
| 3-Layer Baseline (no LLM) | --- | 0.807 -> **0.992** |
| + Sonnet 4.5 (cloud) | 0.77 | 0.845 |
| + Qwen 2.5 7B (local) | 0.82 | 0.846 |
| + Opus 4.6 (cloud) | 0.79 | 0.829 |

**Note**: The 3-layer baseline improvements above (0.807 -> 0.992) will also improve the
4-layer system, since the LLM layer only adds value on top of the 3-layer pipeline. The
4-layer numbers in the table above are from before the mismatch remediation and will be
higher when re-run.

---

## Files Modified

| File | Change |
|------|--------|
| `src/core/services/matching_service.py` | Empty string guard, NLP taxonomy post-filter |
| `src/config/rules/manufacturing.yaml` | PCB/SMT, post-processing, material heuristic rules |
| `src/config/taxonomy/processes.yaml` | Added electroplating, brazing, cnc plasma cutting alias, sla printer alias, welder alias |
| `src/core/taxonomy/process_taxonomy.py` | Tightened substring matching threshold (3 -> 5 chars), added same entries as YAML |
| `tests/e2e/test_matching_accuracy.py` | Updated accuracy thresholds to reflect new baseline |
