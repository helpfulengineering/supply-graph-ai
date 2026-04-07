# Visualization

## Overview

Phase 3.2 introduces a canonical visualization contract for API and CLI consumers.
The first delivery path is API/CLI-first and export-oriented:

- `JSONVizBundle` for machine-readable visualization payloads
- GraphML exports for graph tooling interoperability
- Standalone HTML reports for offline sharing

## Contract

Visualization payloads use schema version `3.2.0` with this top-level shape:

- `schema_version`
- `source_type` (`match_result` or `supply_tree_solution`)
- `generated_at`
- `matching`
- `supply_tree`
- `network`
- `dashboard`
- `artifacts`

## API Endpoints

### Supply Tree Visualization Bundle

- `GET /v1/api/supply-tree/solution/{solution_id}/visualization`
- Returns standard success envelope with a `data` visualization bundle payload.

### Supply Tree Visualization Report

- `GET /v1/api/supply-tree/solution/{solution_id}/report`
- Returns `text/html` report generated from the same canonical visualization bundle.

### GraphML Metadata Normalization

GraphML exports include stable metadata comments:

- `ohm_visualization_schema=3.2.0`
- `source_type=<source>`
- `source_id=<id>`

This applies to GraphML export paths under `supply-tree` routes.

## CLI Commands

### Match

- `ohm match visualize INPUT_FILE [--domain ...] [--format json|html] [--output PATH]`

### Solution

- `ohm solution visualize SOLUTION_ID [--format json|html] [--output PATH]`
- `ohm solution report SOLUTION_ID [--output PATH]`

## Implementation Notes

- Matching visualization datasets include confidence bins, coverage heatmap summaries,
  and gap/guidance projections.
- Supply-tree datasets include nodes, edges, dependency graph, and production sequence.
- Network datasets include facility distribution and capability adjacency with explicit
  placeholder status for route optimization fields that are not yet available.

