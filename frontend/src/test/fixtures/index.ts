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
  domains: ["manufacturing", "cooking"],
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

/** Path-keyed lookup used by the Playwright interceptor (see e2e/mock-api.ts). */
export const fixturesByPath: Record<string, unknown> = {
  "/health": healthFixture,
  "/v1/api/utility/domains": domainsFixture,
  "/v1/api/okh": okhListFixture,
};
