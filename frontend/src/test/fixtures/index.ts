/**
 * Shared mock API fixtures.
 *
 * Single source of truth for mocked responses, consumed by BOTH the MSW node
 * server (vitest unit/component tests) and the Playwright mocked E2E lane. Keep
 * fixtures minimal and representative; feature slices extend this as they add
 * journeys.
 */

export const healthFixture = {
  status: "ok",
  domains: ["cooking", "manufacturing"],
  version: "0.0.0-test",
};

export const domainsFixture = {
  data: {
    domains: [
      { id: "manufacturing", name: "Manufacturing", description: "Hardware manufacturing" },
      { id: "cooking", name: "Cooking & Food Prep", description: "Recipe matching" },
    ],
  },
};

export const metricsFixture = {
  data: {
    total_requests: 1094,
    recent_requests_1h: 111,
    active_requests: 1,
    error_summary: { total_errors: 0 },
  },
};

/** A minimal OKH manifest shaped like the list payload the UI renders. */
function okhItem(
  id: string,
  title: string,
  fn: string,
  processes: string[],
  license: string,
  material: string,
): Record<string, unknown> {
  return {
    id,
    title,
    version: "1.0.0",
    function: fn,
    description: fn,
    keywords: [],
    documentation_language: "en",
    license: { hardware: license, documentation: null, software: null },
    licensor: { name: "OHM Test", email: null, affiliation: null, social: [] },
    contributors: [],
    manufacturing_processes: processes,
    materials: [{ material_id: material, name: material, quantity: 1, unit: "kg", notes: null }],
    design_files: [],
    manufacturing_files: [],
    making_instructions: [],
    parts: [],
    tool_list: [],
    image: null,
    project_link: null,
  };
}

/** Populated OKH list (paginated envelope) with varied facets for browse tests. */
export const okhListFixture = {
  status: "success",
  message: "ok",
  timestamp: "2026-01-01T00:00:00Z",
  request_id: "test",
  pagination: {
    page: 1,
    page_size: 100,
    total_items: 3,
    total_pages: 1,
    has_next: false,
    has_previous: false,
  },
  items: [
    okhItem("okh-0001", "Open Ventilator", "Emergency ventilator", ["3D Printing", "Assembly"], "MIT", "PLA"),
    okhItem("okh-0002", "Face Shield", "Protective face shield", ["3D Printing", "Laser Cutting"], "GPL-2.0", "Acrylic"),
    okhItem("okh-0003", "Test Rig", "Calibration test rig", ["Laser Cutting"], "MIT", "Steel"),
  ],
};

/** Empty OKH list — exercises the empty-state path deterministically. */
export const okhListEmptyFixture = {
  ...okhListFixture,
  pagination: { ...okhListFixture.pagination, total_items: 0 },
  items: [],
};

/** A single OKH manifest (detail payload, fields at top level). */
export const okhDetailFixture = okhListFixture.items[0];

/** Validation result for the OKH validate endpoint. */
export const validationResultFixture = {
  is_valid: true,
  score: 0.92,
  errors: [],
  warnings: ["Missing intended_use documentation"],
  suggestions: ["Add a bill of materials for completeness"],
};

function okwFacility(
  id: string,
  name: string,
  city: string,
  processes: string[],
  access_type: string,
  facility_status: string,
): Record<string, unknown> {
  return {
    id,
    name,
    location: { address: { city, region: "TX", country: "US" }, city, country: "US" },
    manufacturing_processes: processes,
    access_type,
    facility_status,
    description: `${name} in ${city}`,
  };
}

/** OKW search envelope ({results,total,page,page_size}) with varied facets. */
export const okwSearchFixture = {
  results: [
    okwFacility("okw-1", "Laser Fab Lab", "Austin", ["https://en.wikipedia.org/wiki/Laser_cutter"], "Membership", "Active"),
    okwFacility("okw-2", "Community Makerspace", "Austin", ["Assembly"], "Public", "Active"),
    okwFacility("okw-3", "Precision CNC Shop", "Denver", ["https://en.wikipedia.org/wiki/CNC_mill"], "Restricted", "Planned"),
  ],
  total: 3,
  page: 1,
  page_size: 100,
};

export const okwSearchEmptyFixture = { results: [], total: 0, page: 1, page_size: 100 };

/** A single OKW facility (detail payload) with equipment + certifications. */
export const okwDetailFixture = {
  ...okwSearchFixture.results[0],
  description: "A membership laser-cutting lab in Austin.",
  equipment: [
    { make: "Trotec", model: "LS-1630", equipment_type: "https://en.wikipedia.org/wiki/Laser_cutter" },
    { make: "Epilog", model: "Fusion Pro", equipment_type: "https://en.wikipedia.org/wiki/Laser_engraving" },
  ],
  certifications: ["ISO 9001:2015", "OHSAS 18001"],
};

/** Match response envelope: solutions + summary + coverage gaps under `data`. */
export const matchResponseFixture = {
  data: {
    solutions: [
      {
        facility_name: "FabLab Drome",
        facility_id: "okw-1",
        confidence: 0.95,
        score: 0.95,
        rank: 1,
        explanation_human: "✓ FabLab Drome MATCHED (confidence: 95%)\nAll requirements satisfied.",
        tree: { id: "tree-1" },
      },
      {
        facility_name: "Community Makerspace",
        facility_id: "okw-2",
        confidence: 0.6,
        score: 0.6,
        rank: 2,
        explanation_human: "Partial match; some processes unmet.",
        tree: { id: "tree-2" },
      },
    ],
    coverage_gaps: ["CNC Machining"],
    human_summary: { executive: "2 candidate solutions found; coverage 1/2." },
    total_solutions: 2,
    solution_id: "sol-1",
  },
};

/** Visualization bundle (nested under `data`, as the API returns it). */
export const vizBundleFixture = {
  data: {
    schema_version: "3.2.0",
    source_type: "solution",
    generated_at: "2026-01-01T00:00:00Z",
    matching: { overview: { matching_mode: "single-level", score: 0.95, tree_count: 1 } },
    supply_tree: {
      solution_id: "sol-1",
      nodes: [
        {
          id: "n1",
          label: "Frame",
          component_id: null,
          facility_name: "FabLab Drome",
          depth: 0,
          production_stage: "assembly",
          confidence_score: 0.95,
          estimated_cost: null,
          estimated_time: null,
        },
        {
          id: "n2",
          label: "Base Plate",
          component_id: null,
          facility_name: "Community Makerspace",
          depth: 1,
          production_stage: "fabrication",
          confidence_score: 0.9,
          estimated_cost: null,
          estimated_time: null,
        },
      ],
      edges: [{ source: "n2", target: "n1", type: "depends_on" }],
      dependency_graph: { n1: ["n2"] },
      production_sequence: [["n2"], ["n1"]],
      resource_cost: { total_estimated_cost: null, total_estimated_time: null },
    },
    network: {
      facility_distribution: [{ facility_name: "FabLab Drome", tree_count: 1 }],
      route_hints: { status: "not_provided", note: "" },
    },
    dashboard: { kpis: { tree_count: 1, edge_count: 1, stage_count: 2, solution_score: 0.95 } },
    artifacts: {},
  },
};

/** Path-keyed lookup used by the Playwright interceptor (see e2e/mock-api.ts). */
/** Saved supply-tree solutions list (envelope: data.result[]). */
export const solutionsListFixture = {
  data: {
    result: [
      {
        id: "sol-1",
        okh_id: "okh-0001",
        okh_title: "Open Ventilator",
        matching_mode: "single-level",
        tree_count: 1,
        facility_count: 2,
        score: 0.95,
        created_at: "2026-07-03T12:00:00Z",
      },
      {
        id: "sol-2",
        okh_id: "okh-0002",
        okh_title: "Face Shield",
        matching_mode: "single-level",
        tree_count: 1,
        facility_count: 1,
        score: 0.6,
        created_at: "2026-07-02T09:00:00Z",
      },
    ],
  },
};

export const solutionsEmptyFixture = { data: { result: [] } };

export const fixturesByPath: Record<string, unknown> = {
  "/health": healthFixture,
  "/v1/api/utility/domains": domainsFixture,
  "/v1/api/utility/metrics": metricsFixture,
  "/v1/api/okh": okhListFixture,
  "/v1/api/okh/okh-0001": okhDetailFixture,
  "/v1/api/okh/validate": validationResultFixture,
  "/v1/api/okw/search": okwSearchFixture,
  "/v1/api/okw/okw-1": okwDetailFixture,
  "/v1/api/okw/validate": validationResultFixture,
  "/v1/api/match": matchResponseFixture,
  "/v1/api/supply-tree/solutions": solutionsListFixture,
  "/v1/api/supply-tree/solution/sol-1/visualization": vizBundleFixture,
};
