# ADR: Canonical File Type Taxonomy

## Status

Accepted

## Date

2026-07-09

## Context

File extension and MIME handling was fragmented across 6+ modules (`file_categorization.py`,
`file_processor.py`, platform detectors, `okh_file_resolver.py`, frontend `okhFileHref.ts`).
The OKH file proxy UI showed only basenames, making duplicate filenames (e.g. multiple
`README.md`) indistinguishable, and opened all files as raw browser tabs.

## Decision

Create a single **File Type Taxonomy** (`src/core/taxonomy/file_type_taxonomy.py`) as the
authoritative source for:

1. **Technical type** — what the bytes are (`mesh_stl`, `document_pdf`, …)
2. **OKH role** — manifest semantics (`design`, `manufacturing`, `grey_zone`, …)
3. **Render tier** — UI behavior (`native_inline`, `text_viewer`, `wasm_3d`, `download_only`)

Path presentation uses `display_path` / `directory` derived from `file_path_display.py`
(strip GitHub/GitLab URL prefixes; keep storage-relative paths as-is).

### Design choices

- Canonical IDs are lowercase `snake_case` strings.
- Extensions map many-to-one to canonical IDs; MIME types are secondary.
- Grey-zone types (`.stl`, `.dxf`) resolve OKH role from directory context (ported from
  `file_categorization.py` — no new heuristics).
- Unknown extensions → `unknown` type, `download_only` render tier.
- 3D WASM preview is **deferred**; `wasm_3d` tier shows metadata + download only.

## Consequences

- OKH detail responses enrich file refs with `display_path`, `directory`, `file_type`,
  `render_tier`, `mime_type`.
- Frontend groups files by directory within each manifest bucket.
- Consolidation of extension lists proceeds incrementally; taxonomy is the target SSOT.

## Phase 2 (deferred)

STL/OBJ in-browser preview via lazy-loaded three.js chunk; DXF via separate 2D viewer.
