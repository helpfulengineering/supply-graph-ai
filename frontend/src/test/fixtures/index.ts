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

/** Path-keyed lookup used by the Playwright interceptor (see e2e/mock-api.ts). */
export const fixturesByPath: Record<string, unknown> = {
  "/health": healthFixture,
  "/v1/api/utility/domains": domainsFixture,
  "/v1/api/okh": okhListFixture,
  "/v1/api/okh/okh-0001": okhDetailFixture,
  "/v1/api/okh/validate": validationResultFixture,
  "/v1/api/okw/search": okwSearchFixture,
  "/v1/api/okw/okw-1": okwDetailFixture,
  "/v1/api/okw/validate": validationResultFixture,
};
