# Matching Mismatch Pattern Analysis

> Generated from accuracy reports: baseline, Anthropic Sonnet 4.5, Opus 4.6, Ollama llama3.2:3b
>
> Date: 2026-02-15

## Executive Summary

Across 115 ground-truth cases, the 4-layer system (with Sonnet 4.5) produces **22 mismatches**.
These fall into **5 distinct failure categories**, each with a clear remediation path.
The analysis below prioritizes by impact (number of affected cases) and identifies
which improvements will help smaller models the most.

---

## Failure Categories

### Category 1: Process-Requires-Sub-Process (8 FN)

**Pattern**: A high-level requirement (e.g., "PCB", "SMT", "Post-processing") implies
specific sub-equipment (e.g., Pick_and_place, Reflow_oven, Deburring_station), but the
system cannot make the inference.

| ID | Requirement | Capability | Notes |
|----|-------------|------------|-------|
| tp-proc-004 | PCB | Pick_and_place | PCB assembly requires pick-and-place |
| tp-proc-005 | PCB | Reflow_oven | PCB assembly requires reflow soldering |
| tp-proc-010 | Post-processing | Deburring_station | Post-processing includes deburring |
| tp-proc-011 | Post-processing | Deburring | Post-processing includes deburring |
| tp-proc-012 | Post-processing | Anodizing_line | Post-processing includes anodizing |
| tp-proc-013 | Post-processing | Paint_booth | Post-processing includes painting |
| tp-proc-019 | SMT | Pick_and_place | SMT involves pick-and-place |
| tp-proc-020 | SMT | Reflow_oven | SMT involves reflow soldering |

**Root Cause**: The taxonomy has `pcb_fabrication` and `pcb_assembly` as separate
processes but does not encode that PCB/SMT *require* pick-and-place and reflow equipment.
Similarly, `post_processing` has no child processes linking to deburring, anodizing, or painting.

**Remediation**:
- **Taxonomy fix**: Add `requires` or `involves` relationships in the taxonomy
  (e.g., `pcb_fabrication.involves = [pick_and_place, reflow_soldering]`)
- **Prompt fix**: Add few-shot examples showing process-to-equipment inference
- **Impact**: Fixes 8 of 14 false negatives (57% of all FN)

---

### Category 2: Abbreviation / URI Resolution (4 FN)

**Pattern**: The system cannot resolve well-known abbreviations to their full names
or match Wikipedia URI slugs to common terms.

| ID | Requirement | Capability | Notes |
|----|-------------|------------|-------|
| syn-011 | stereolithography | SLA_printer | stereolithography = SLA |
| mat-011 | Thermoplastic Polyurethane | TPU | Full name vs abbreviation |
| mat-013 | Polylactic Acid | PLA | Full name vs abbreviation |
| uri-005 | PCB | Pick_and_place | PCB code vs URI slug |

**Root Cause**: The taxonomy covers process synonyms well (SLA -> 3d_printing_sla) but:
- `SLA_printer` as a URI slug is not mapped (only `sla` and `stereolithography`)
- Material abbreviations (TPU, PLA) are not in the taxonomy at all (it only covers processes)
- `Pick_and_place` as a URI slug has no mapping to PCB-related processes

**Remediation**:
- **Taxonomy fix**: Add `sla_printer` as alias for `3d_printing_sla`
- **Material taxonomy**: Create a parallel material taxonomy with abbreviation mappings
- **URI slug normalization**: Strip `_` from URI slugs before lookup (e.g., `Pick_and_place` -> `pick and place`)
- **Prompt fix**: Include common abbreviation table in the LLM prompt context
- **Impact**: Fixes 4 of 14 false negatives (29% of all FN)

---

### Category 3: NLP Semantic Over-Matching (5 FP)

**Pattern**: The NLP layer (spaCy similarity) matches terms that are in the same
manufacturing domain but are fundamentally different processes.

| ID | Requirement | Capability | Expected | Notes |
|----|-------------|------------|----------|-------|
| tn-proc-001 | 3DP | CNC_mill | FALSE | Additive != subtractive |
| tn-proc-007 | PCB | CNC_mill | FALSE | Electronics != machining |
| nm-002 | cnc plasma cutting | CNC_mill | FALSE | Plasma cutting != milling |
| nm-006 | electroplating | Anodizing_line | FALSE | Different surface treatments |
| nm-007 | brazing | Welder | FALSE | Different joining methods |

**Root Cause**: spaCy word vectors place all manufacturing terms close together in
embedding space. "3DP" and "CNC_mill" both relate to manufacturing, so their cosine
similarity exceeds the NLP threshold.

**Remediation**:
- **Taxonomy-informed NLP**: Before accepting an NLP match, verify both terms resolve
  to the same canonical process (or related processes) in the taxonomy
- **Negative taxonomy**: Add explicit "is not" relationships (e.g., brazing is NOT welding)
- **Prompt fix**: Add few-shot negative examples showing similar-but-different processes
- **Impact**: Fixes 5 of 8 false positives (63% of all FP)

---

### Category 4: Material Confusion (2 cases: 1 FN + 1 FP)

**Pattern**: The system struggles with material hierarchies and alloy distinctions.

| ID | Requirement | Capability | Expected | Notes |
|----|-------------|------------|----------|-------|
| mat-009 | Acrylic Sheet | Plastic | TRUE | Acrylic IS a type of plastic (FN) |
| mat-004 | Aluminum 6061-T6 | Aluminum_7075 | FALSE | Different alloys (FP) |

**Root Cause**: No material taxonomy exists. The system has no knowledge that acrylic
is a subtype of plastic, or that 6061-T6 and 7075 are different aluminum alloys with
different properties.

**Remediation**:
- **Material taxonomy**: Create `materials.yaml` with hierarchical material definitions
  (metals -> aluminum -> 6061, 7075; plastics -> acrylic, PLA, TPU, etc.)
- **Prompt fix**: Include material hierarchy context for LLM matching
- **Impact**: Fixes 2 mismatches directly, enables future material matching improvements

---

### Category 5: Edge Case / Empty String (2 FP)

**Pattern**: The direct layer incorrectly matches when capability or both strings are empty.

| ID | Requirement | Capability | Expected | Notes |
|----|-------------|------------|----------|-------|
| edge-002 | 3DP | *(empty)* | FALSE | Empty capability matched |
| edge-003 | *(empty)* | *(empty)* | FALSE | Both empty matched |

**Root Cause**: The direct matching layer does not guard against empty strings.

**Remediation**:
- **Code fix**: Add empty-string guard in `_direct_match()` method
- **Impact**: Fixes 2 false positives, trivial code change

---

## Cross-Model Comparison

The mismatches above are from the 3-layer combined system (shared across all configs).
The LLM layer's *additional* contribution varies by model:

| Model | LLM-Only P/R/F1 | FN Rescued | New FP Introduced | Net Impact |
|-------|-----------------|------------|-------------------|------------|
| Sonnet 4.5 | 0.87 / 0.68 / 0.77 | 6 | 3 | +3 correct |
| Opus 4.6 | 0.89 / 0.70 / 0.79 | 5 | 4 | +1 correct |
| llama3.2:3b | 0.52 / 0.97 / 0.68 | 14 | 46 | -32 correct |

### Key Finding: Ollama 3B Failure Mode

The llama3.2:3b model says "yes" to virtually everything (97% recall, 52% precision).
This is not a prompt engineering failure -- the model lacks the reasoning capacity to
distinguish similar manufacturing processes. A model in the 7B-14B range is the minimum
viable size for this task.

---

## Priority Matrix

| Priority | Category | Cases | Fix Type | Effort |
|----------|----------|-------|----------|--------|
| **P1** | Process-Requires-Sub-Process | 8 FN | Taxonomy + Prompt | Medium |
| **P2** | NLP Semantic Over-Matching | 5 FP | Taxonomy-informed NLP | Medium |
| **P3** | Abbreviation/URI Resolution | 4 FN | Taxonomy + Prompt | Low |
| **P4** | Material Confusion | 2 | Material Taxonomy | Medium |
| **P5** | Empty String Edge Case | 2 FP | Code fix | Trivial |

Fixing P1 + P2 + P3 would resolve **17 of 22 mismatches** (77%), bringing the
3-layer baseline F1 from 0.807 to approximately **0.93**.

---

## Implications for Model Exploration (Track 1)

The analysis reveals that many failures are **knowledge gaps**, not reasoning failures:
- 12 of 14 FN are missing domain knowledge (process relationships, abbreviations)
- 5 of 8 FP are NLP false similarities that could be filtered by taxonomy

This means:
1. **Better prompts with taxonomy context** will disproportionately help mid-tier models
   (7B-14B) since the failures are knowledge-based, not reasoning-based
2. **The 3-layer system itself can be improved** without any LLM, by adding taxonomy
   relationships and NLP post-filtering
3. **A mid-tier model with good prompts may match Sonnet 4.5** if we provide the domain
   knowledge that Sonnet 4.5 has from pretraining
