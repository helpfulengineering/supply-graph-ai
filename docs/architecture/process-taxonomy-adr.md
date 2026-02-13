# ADR: Canonical Process Taxonomy

## Status

Accepted

## Date

2026-02-12

## Context

The system previously had 6+ independent normalization/mapping functions for
manufacturing process names, each with its own incomplete dictionary:

1. `matching_service.py` -- `_normalize_process_name` (15 mappings) + `_tsdc_to_process_uri` (6 mappings)
2. `okh_validator.py` -- `_is_valid_manufacturing_process` (9 hardcoded Wikipedia URIs)
3. `okw_validator.py` -- `_is_valid_manufacturing_process` (9 hardcoded Wikipedia URIs)
4. `generation/engine.py` -- `_normalize_manufacturing_processes` (~30 mappings)
5. `generation/layers/heuristic.py` -- `process_mapping` (~10 mappings)
6. `matching/layers/base.py` -- `normalize_process_name` (URI extraction only)

This fragmentation caused:

- **Namespace mismatch**: OKH manifests use TSDC short codes ("CNC", "3DP"),
  while OKW facilities use Wikipedia URIs, and the validator only accepted URIs.
- **Inconsistent matching**: Different normalization logic in different code paths
  meant the same process could match or fail depending on which path was taken.
- **Maintenance burden**: Adding a new process type required updating all 6+ locations.

The original approach used Wikipedia article URLs as process identifiers.
This had fundamental problems:
- Wikipedia articles are not stable identifiers (rename, merge, delete)
- No hierarchy (no way to know "FDM" is-a "3D printing")
- Inconsistent granularity across articles
- Not a controlled vocabulary

## Decision

Create a single canonical **Process Taxonomy** (`src/core/taxonomy/process_taxonomy.py`)
as the authoritative source of truth for all manufacturing process identification.

### Design choices

- **Canonical IDs are lowercase snake_case strings** (e.g., `3d_printing`, `cnc_machining`).
  These are internal identifiers, not URIs.
- **Many-to-one alias table** maps every known form (TSDC codes, Wikipedia URIs,
  plain English names, abbreviations) to canonical IDs.
- **Hierarchy** supports parent-child relationships (e.g., `3d_printing_fdm` -> `3d_printing`).
- **Unknown inputs return `None`** rather than raising, allowing the NLP matching
  layer to handle truly novel inputs via fuzzy matching. This is critical for
  heterogeneous, ad hoc supply chain scenarios.
- **Singleton pattern** -- instantiated once at module load time. Pure data, no
  side effects, no dependency injection needed.

### TSDC code alignment

TSDC (Technology-specific Documentation Criteria) from DIN SPEC 3105 defines
documentation requirement modules, not a process taxonomy. However, TSDC codes
("3DP", "CNC", "LAS", "PCB", "ASM", "WEL") are widely used in the OKH ecosystem,
so the taxonomy provides bidirectional TSDC code mapping. Child processes inherit
their parent's TSDC code via `get_tsdc_code()`.

### Why not use an external ontology?

Options considered:

1. **IOF (Industrial Ontologies Foundry)** -- NIST BFO-based, formal, comprehensive.
   Too heavy for a system designed for ad hoc crisis-scenario supply chains.
2. **Wikidata Q-numbers** -- Stable, hierarchical, multilingual. Requires network
   access and introduces external dependency. Could be a future enhancement.
3. **UNSPSC** -- Product/service classification, not a process taxonomy.
4. **Custom internal taxonomy** -- Chosen. Lightweight, offline, covers the specific
   processes relevant to open hardware manufacturing.

The taxonomy is designed to be **extensible**: adding a new process requires
adding one `ProcessDefinition` entry with its aliases.

## Consequences

### Positive

- Single source of truth for process identification
- TSDC codes, Wikipedia URIs, and plain names all resolve correctly
- Hierarchy enables smarter matching (sibling processes score higher)
- Adding new processes requires updating only one file
- Validators now accept TSDC codes directly (fixed WF-4 test gap)

### Negative

- All 6 consumer sites needed refactoring (completed)
- The alias table must be maintained as new processes are discovered
- Substring matching in `normalize()` could cause false positives for
  very short inputs (mitigated by 3-character minimum)

## Files

- **New**: `src/core/taxonomy/__init__.py`, `src/core/taxonomy/process_taxonomy.py`
- **Tests**: `tests/core/taxonomy/test_process_taxonomy.py` (164 tests)
- **Refactored consumers**: `matching_service.py`, `okh_validator.py`,
  `okw_validator.py`, `engine.py`, `heuristic.py`, `base.py`,
  `generate_synthetic_data.py`
