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
      {
        id: "manufacturing",
        name: "Manufacturing",
        description: "Hardware manufacturing",
      },
      {
        id: "cooking",
        name: "Cooking & Food Prep",
        description: "Recipe matching",
      },
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
    materials: [
      {
        material_id: material,
        name: material,
        quantity: 1,
        unit: "kg",
        notes: null,
      },
    ],
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
    okhItem(
      "okh-0001",
      "Open Ventilator",
      "Emergency ventilator",
      ["3D Printing", "Assembly"],
      "MIT",
      "PLA",
    ),
    okhItem(
      "okh-0002",
      "Face Shield",
      "Protective face shield",
      ["3D Printing", "Laser Cutting"],
      "GPL-2.0",
      "Acrylic",
    ),
    okhItem(
      "okh-0003",
      "Test Rig",
      "Calibration test rig",
      ["Laser Cutting"],
      "MIT",
      "Steel",
    ),
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
    location: {
      address: { city, region: "TX", country: "US" },
      city,
      country: "US",
    },
    manufacturing_processes: processes,
    access_type,
    facility_status,
    description: `${name} in ${city}`,
  };
}

/** OKW search envelope ({results,total,page,page_size}) with varied facets. */
export const okwSearchFixture = {
  results: [
    okwFacility(
      "okw-1",
      "Laser Fab Lab",
      "Austin",
      ["https://en.wikipedia.org/wiki/Laser_cutter"],
      "Membership",
      "Active",
    ),
    okwFacility(
      "okw-2",
      "Community Makerspace",
      "Austin",
      ["Assembly"],
      "Public",
      "Active",
    ),
    okwFacility(
      "okw-3",
      "Precision CNC Shop",
      "Denver",
      ["https://en.wikipedia.org/wiki/CNC_mill"],
      "Restricted",
      "Planned",
    ),
  ],
  total: 3,
  page: 1,
  page_size: 100,
};

export const okwSearchEmptyFixture = {
  results: [],
  total: 0,
  page: 1,
  page_size: 100,
};

/** A single OKW facility (detail payload) with equipment + certifications. */
export const okwDetailFixture = {
  ...okwSearchFixture.results[0],
  description: "A membership laser-cutting lab in Austin.",
  equipment: [
    {
      make: "Trotec",
      model: "LS-1630",
      equipment_type: "https://en.wikipedia.org/wiki/Laser_cutter",
    },
    {
      make: "Epilog",
      model: "Fusion Pro",
      equipment_type: "https://en.wikipedia.org/wiki/Laser_engraving",
    },
  ],
  certifications: ["ISO 9001:2015", "OHSAS 18001"],
};

/** Process taxonomy (SuccessResponse envelope from GET /api/taxonomy). */
export const taxonomyFixture = {
  success: true,
  message: "Taxonomy retrieved successfully",
  data: {
    total: 3,
    source: "test",
    processes: [
      {
        canonical_id: "3d_printing",
        display_name: "3D Printing",
        parent: null,
        children: ["3d_printing_fdm"],
        aliases: [],
      },
      {
        canonical_id: "3d_printing_fdm",
        display_name: "FDM 3D Printing",
        parent: "3d_printing",
        children: [],
        aliases: [],
      },
      {
        canonical_id: "laser_cutting",
        display_name: "Laser Cutting",
        parent: null,
        children: [],
        aliases: [],
      },
    ],
  },
};

/** Unified network surface (flat envelope, not nested in data). */
export const networkSpacesFixture = {
  success: true,
  spaces: [
    {
      id: "okw-1",
      name: "Laser Fab Lab",
      lat: 30.2711,
      lon: -97.7437,
      source: "local",
      city: "Austin",
      region: "TX",
      country: "US",
      status: "active",
      processes: ["laser_cutting"],
      access_type: "Membership",
      url: null,
      ambiguous: false,
    },
    {
      id: "okw-2",
      name: "Community Makerspace",
      lat: 30.25,
      lon: -97.75,
      source: "local",
      city: "Austin",
      region: "TX",
      country: "US",
      status: "active",
      processes: ["assembly"],
      access_type: "Public",
      url: null,
      ambiguous: false,
    },
    {
      id: "urn:mak:space/lazio",
      name: "FabLab Lazio Roma",
      lat: 41.8902,
      lon: 12.5179,
      source: "mom",
      city: "Rome",
      region: null,
      country: "IT",
      status: "active",
      processes: ["cnc_machining"],
      access_type: null,
      url: "https://lazio",
      ambiguous: false,
    },
  ],
  total: 3,
  local_count: 2,
  mom_count: 1,
  dropped_no_coords: 1,
  mom_available: true,
};

/** Reverse-match: designs a facility can produce (data.designs[]). */
export const facilityDesignsFixture = {
  data: {
    okw_id: "okw-1",
    facility_name: "Laser Fab Lab",
    designs: [
      {
        okh_id: "okh-0001",
        okh_title: "Open Ventilator",
        confidence: 0.95,
        rank: 1,
      },
      {
        okh_id: "okh-0002",
        okh_title: "Face Shield",
        confidence: 0.62,
        rank: 2,
      },
    ],
    total_designs: 2,
    designs_considered: 3,
  },
};

export const facilityDesignsEmptyFixture = {
  data: {
    okw_id: "okw-1",
    facility_name: "Laser Fab Lab",
    designs: [],
    total_designs: 0,
    designs_considered: 3,
  },
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
        explanation_human:
          "✓ FabLab Drome MATCHED (confidence: 95%)\nAll requirements satisfied.",
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
    matching: {
      overview: { matching_mode: "single-level", score: 0.95, tree_count: 1 },
    },
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
    dashboard: {
      kpis: {
        tree_count: 1,
        edge_count: 1,
        stage_count: 2,
        solution_score: 0.95,
      },
    },
    artifacts: {},
  },
};

export const whoamiAdminFixture = {
  key_id: "00000000-0000-0000-0000-0000000000aa",
  name: "Admin key",
  permissions: ["read", "write", "admin"],
  account_id: "00000000-0000-0000-0000-000000000001",
  subject_did: null,
};

export const securityPolicyFixture = {
  mode: "peacetime",
  require_auth_for_writes: false,
  custodial_keys_allowed: true,
  grant_ttl_days: 90,
  recovery: "reissuance",
  trust_bootstrap: "tofu_registry",
  mdns_advertise: true,
  metadata_logging: "full",
  registry_attestations: "trust_on_follow",
  anonymous_submission_allowed: true,
  open_registration: true,
};

export const registrationFixture = {
  account_id: "00000000-0000-0000-0000-0000000000cc",
  display_name: "Ada Lovelace",
  did: "did:key:zAdaRegistered",
  key: {
    key_id: "00000000-0000-0000-0000-0000000000cd",
    name: "Ada Lovelace (first key)",
    permissions: ["read", "write"],
    created_at: "2026-08-30T00:00:00Z",
    revoked: false,
    token: "ohm_registered_once",
  },
  recovery_code: "ohm_recovery_once",
};

export const recoveredFixture = {
  ...registrationFixture,
  key: { ...registrationFixture.key, token: "ohm_recovered_token" },
  recovery_code: "ohm_recovery_replacement",
};

export const apiKeysFixture = [
  {
    key_id: "00000000-0000-0000-0000-0000000000aa",
    name: "Admin key",
    description: null,
    permissions: ["read", "write", "admin"],
    created_at: "2026-01-01T00:00:00Z",
    last_used_at: null,
    expires_at: null,
    revoked: false,
    token: null,
  },
];

export const accountsFixture = [
  {
    id: "00000000-0000-0000-0000-000000000001",
    display_name: "Local admin",
    kind: "person",
    created_at: "2026-01-01T00:00:00Z",
    disabled: false,
  },
];

export const identityFixture = {
  did: "did:key:z6MktestPerson0000000000000000000000001",
  kind: "person",
  display_name: "Local admin",
  created_at: "2026-01-01T00:00:00Z",
  account_id: "00000000-0000-0000-0000-000000000001",
  links_in: [],
  custodial: true,
};

export const spaceIdentityFixture = {
  did: "did:key:z6MktestSpace00000000000000000000000001",
  kind: "space",
  display_name: "Test Space",
  created_at: "2026-01-01T00:00:00Z",
  account_id: "00000000-0000-0000-0000-000000000001",
  links_in: [],
  custodial: true,
};

export const grantsFixture = [
  {
    grant_id: "00000000-0000-0000-0000-0000000000g1",
    issuer_did: "did:key:z6MktestNode000000000000000000000000001",
    subject_did: identityFixture.did,
    permissions: ["write"],
    coarse_floor: [],
    scope: { kind: "space", target: spaceIdentityFixture.did, v: 1 },
    issued_at: "2026-01-01T00:00:00Z",
    not_before: null,
    expires_at: "2026-04-01T00:00:00Z",
  },
];

export const spaceClaimsFixture = [
  {
    space_did: spaceIdentityFixture.did,
    admin_did: identityFixture.did,
    claimed_at: "2026-01-01T00:00:00Z",
    claim_method: "tofu",
    signature: "ab",
  },
];

export const attestationsFixture = [
  {
    attestation_id: "00000000-0000-0000-0000-0000000000a1",
    type: "certified",
    issuer_did: "did:key:z6MktestNode000000000000000000000000001",
    subject_did: identityFixture.did,
    content_hash: "sha256:bundlehash0000000000000000000000000001",
    claim: { version: "1.0.0" },
    created_at: "2026-01-01T00:00:00Z",
    expires_at: null,
    signature: "cd",
  },
  {
    attestation_id: "00000000-0000-0000-0000-0000000000a2",
    type: "domain_bound",
    issuer_did: "did:key:z6MktestNode000000000000000000000000001",
    subject_did: identityFixture.did,
    content_hash: null,
    claim: { domain: "example.org" },
    created_at: "2026-01-02T00:00:00Z",
    expires_at: null,
    signature: "ef",
  },
  {
    attestation_id: "00000000-0000-0000-0000-0000000000a3",
    type: "vouch",
    issuer_did: spaceIdentityFixture.did,
    subject_did: identityFixture.did,
    content_hash: null,
    claim: {},
    created_at: "2026-01-03T00:00:00Z",
    expires_at: null,
    signature: "gh",
  },
];

export const pinRecordFixture = {
  pinned_at: "2026-01-01T00:00:00Z",
  pinned_by: "tester",
  manifest_content_hash: "manifest-hash-leaf",
  file_hashes: {},
  note: null,
};

export const domainBindStartFixture = {
  binding: {
    binding_id: "00000000-0000-0000-0000-0000000000b1",
    subject_did: identityFixture.did,
    kind: "domain",
    external_id: "domain:example.org",
    evidence: { domain: "example.org" },
    challenge: "test-challenge-token",
    verified: false,
    verified_at: null,
    created_at: "2026-01-01T00:00:00Z",
    signature: "sig",
  },
  well_known_url: "https://example.org/.well-known/ohm-did.json",
  well_known_document: {
    did: identityFixture.did,
    challenge: "test-challenge-token",
    method: "ohm-domain-bind-v1",
  },
};

export const bindingsFixture = [
  {
    binding_id: "00000000-0000-0000-0000-0000000000b2",
    subject_did: identityFixture.did,
    kind: "oauth",
    external_id: "oauth:github:octocat",
    evidence: {},
    challenge: null,
    verified: true,
    verified_at: "2026-01-01T00:00:00Z",
    created_at: "2026-01-01T00:00:00Z",
    signature: "sig2",
  },
];

export const directoryFixture = [
  {
    did: identityFixture.did,
    display_name: "Local admin",
    base_url: "https://ohm.example.org",
    domain: "example.org",
    verified_bindings: ["domain:example.org"],
    updated_at: "2026-01-01T00:00:00Z",
  },
];

export const federationStatusFixture = {
  did: "did:key:z6MktestNode000000000000000000000000001",
  display_name: "Test Node",
  role: "full",
  catalog_record_count: 2,
  merkle_root: "abc123",
  peer_count: 1,
  followed_peer_count: 1,
  sync_interval_sec: 300,
  mdns_enabled: true,
  background_sync_running: false,
  manual_peers: [],
  seed_peer_url: "https://openhardwaremanager.org",
  metrics: {
    total_records_pulled: 0,
    total_records_skipped: 0,
    total_sync_runs: 0,
    total_digest_requests_inbound: 0,
    total_digest_requests_outbound: 0,
    total_rate_limit_rejections: 0,
    last_sync_at: null,
    last_background_sync_at: null,
    per_peer_pulled: {},
  },
};

export const federationPeersFixture = {
  peers: [
    {
      did: "did:key:z6MktestPeer000000000000000000000000001",
      base_url: "http://peer-b:8001",
      display_name: "Peer B",
      source: "manual",
      followed: true,
      last_seen_at: "2026-01-01T00:00:00Z",
      last_sync_at: null,
      records_synced: 0,
    },
  ],
  total: 1,
};

export const federationSyncFixture = {
  results: [
    {
      peer_did: "did:key:z6MktestPeer000000000000000000000000001",
      base_url: "http://peer-b:8001",
      pulled: 1,
      skipped: 0,
      errors: [],
    },
  ],
  total_pulled: 1,
};

export const provenanceFixture = {
  authored_by: [{ external_id: "name:Test Author", role: null }],
  published_by: null,
  on_behalf_of: null,
  signed_by: null,
  signature: "",
};

export const visibilityFixture = {
  id: "00000000-0000-0000-0000-000000000001",
  visibility: "private",
};

export const disclosureFixture = {
  id: "okw-1",
  disclosure: {
    followers: { groups: ["identity"] },
    public: { groups: ["identity"] },
  },
};

export const disclosurePreviewFixture = {
  id: "okw-1",
  audience: "followers",
  visibility: "private",
  exported: false,
  groups: ["identity"],
  facility: {
    id: "okw-1",
    name: "Test Fab Lab",
    facility_status: "Active",
  },
};

export const packageListFixture = {
  status: "success",
  message: "ok",
  timestamp: "2026-01-01T00:00:00Z",
  request_id: "test",
  pagination: {
    page: 1,
    page_size: 50,
    total_items: 2,
    total_pages: 1,
    has_next: false,
    has_previous: false,
  },
  items: [
    {
      package_name: "demo/widget",
      version: "1.0.0",
      okh_manifest_id: "okh-0001",
      build_timestamp: "2026-01-01T00:00:00Z",
      total_files: 3,
      total_size_bytes: 1024,
      build_options: {},
      package_path: "/tmp/packages/demo/widget/1.0.0",
    },
    {
      package_name: "demo/widget",
      version: "1.1.0",
      okh_manifest_id: "okh-0001",
      build_timestamp: "2026-02-01T00:00:00Z",
      total_files: 4,
      total_size_bytes: 2048,
      build_options: {},
      package_path: "/tmp/packages/demo/widget/1.1.0",
    },
  ],
};

export const packageMetadataFixture = {
  status: "success",
  message: "ok",
  timestamp: "2026-01-01T00:00:00Z",
  request_id: "test",
  data: {
    metadata: packageListFixture.items[0],
  },
};

/**
 * The identities this instance holds — one person, one space.
 *
 * The Identities panel reads this list, and it was the one settings subtab with
 * no fixture at all: the mocked lane never opened it, so it fell through to a
 * network the lane does not have.
 */
export const identitiesFixture = [identityFixture, spaceIdentityFixture];

/**
 * LLM credentials, one configured and one not.
 *
 * Both states matter to the panel — a configured provider shows a masked key
 * and a Test button, an unconfigured one shows the form — and a fixture with
 * only one of them exercises half the component.
 *
 * The masked key is masked here too. A fixture is a file in a public
 * repository, and "it is only test data" is how a shape that looks like a
 * credential ends up in a search index.
 */
export const llmCredentialsFixture = {
  credentials: [
    {
      provider: "anthropic",
      model: "claude-sonnet-5",
      masked_key: "sk-ant-…demo",
      configured: true,
    },
    { provider: "openai", model: null, masked_key: "", configured: false },
  ],
};

/**
 * The saved-solutions browse: one row, pointing at the one solution the
 * visualization fixture answers for, so the list and the page it opens agree.
 *
 * Envelope is `data.result` because that is what the paginated list decorator
 * emits and what listSolutions reads. Two rows would be more convincing and
 * less useful — the second id has no visualization bundle behind it, so the
 * card would lead to an error the demo cannot explain.
 */
export const solutionsListFixture = {
  data: {
    result: [
      {
        id: "sol-1",
        okh_id: "okh-0001",
        okh_title: "Foldable Solar Dryer",
        facility_name: "FabLab Drome",
        matching_mode: "single-level",
        tree_count: 1,
        facility_count: 1,
        score: 0.95,
        created_at: "2026-01-01T00:00:00Z",
      },
    ],
  },
};

/** Path-keyed lookup used by the Playwright interceptor (see e2e/mock-api.ts). */
/**
 * Cooking-domain browse fixtures.
 *
 * Shape is the paginated envelope `fetchAllRecipes`/`fetchAllKitchens` read
 * (`items` + `pagination` at the top level, not nested under `data`), with
 * `has_next: false` so the paging loop terminates on the first request.
 */
export const recipesFixture = {
  items: [
    {
      id: "recipe-1",
      name: "Sourdough Loaf",
      ingredients: ["flour", "water", "salt", "starter"],
      instructions: ["Mix", "Bulk ferment", "Shape", "Bake"],
      equipment: ["oven", "dutch oven", "mixing bowl"],
      domain: "cooking",
    },
    {
      id: "recipe-2",
      name: "Miso Soup",
      ingredients: ["dashi", "miso paste", "tofu"],
      instructions: ["Heat dashi", "Whisk in miso"],
      equipment: ["saucepan"],
      domain: "cooking",
    },
  ],
  pagination: { has_next: false, total_items: 2 },
};

export const kitchensFixture = {
  items: [
    {
      id: "kitchen-1",
      name: "Community Kitchen",
      appliances: ["oven", "stovetop"],
      tools: ["dutch oven", "mixing bowl"],
      ingredients: ["flour", "water", "salt"],
      domain: "cooking",
    },
    {
      id: "kitchen-2",
      name: "Pop-Up Canteen",
      appliances: ["stovetop"],
      tools: ["saucepan"],
      ingredients: ["dashi", "miso paste"],
      domain: "cooking",
    },
  ],
  pagination: { has_next: false, total_items: 2 },
};


/**
 * Assets.
 *
 * Ids are real UUIDs, not "asset-1". The API declares them as `UUID` path
 * params, unlike OKH/OKW's string ids, so a readable placeholder makes the
 * real backend answer 422 — and the mocked lanes would then be measuring an
 * error panel while reporting the page as fine.
 */
export const ASSET_ID = "11111111-1111-4111-8111-111111111111";
export const ASSET_ID_B = "22222222-2222-4222-8222-222222222222";

const pumpState = {
  component_name: "Pump assembly",
  condition: "damaged",
  repair_feasible: false,
  harvest_viable: true,
  source_required: null,
  notes: "Impeller cracked",
  observed_at: "2026-08-09T10:00:00Z",
  assessed_by: "ana",
  claimed_by: null,
  claimed_at: null,
};

export const assetDetailFixture = {
  id: ASSET_ID,
  manifest_id: "okh-0001",
  asset_tag: "OHM-0042",
  location: "Bay 3",
  status: "under_triage",
  component_states: [pumpState],
  last_triaged_at: "2026-08-09T10:00:00Z",
  triage_notes: "Back panel removed for access.",
  message: "Asset record retrieved",
};

export const assetListFixture = {
  assets: [
    assetDetailFixture,
    {
      id: ASSET_ID_B,
      manifest_id: "okh-0001",
      asset_tag: "OHM-0043",
      location: null,
      status: "active",
      component_states: [],
      last_triaged_at: null,
      triage_notes: null,
      message: "",
    },
  ],
  total: 2,
  message: "2 asset(s)",
};

export const triageChecklistFixture = {
  asset_id: ASSET_ID,
  manifest_id: "okh-0001",
  asset_tag: "OHM-0042",
  status: "under_triage",
  last_triaged_at: "2026-08-09T10:00:00Z",
  items: [
    {
      component_name: "Pump assembly",
      assessed: true,
      replaceable: true,
      salvageable: true,
      consumable: false,
      part_number: "P-1042",
      current_condition: "damaged",
      current_state: pumpState,
    },
    {
      component_name: "Control board",
      assessed: false,
      replaceable: true,
      salvageable: false,
      consumable: false,
      part_number: "CB-7",
      current_condition: null,
      current_state: null,
    },
  ],
  total_components: 2,
  assessed_count: 1,
  pending_count: 1,
  message: "1/2 components assessed",
};

export const triageReportFixture = {
  asset_id: ASSET_ID,
  manifest_id: "okh-0001",
  asset_tag: "OHM-0042",
  last_triaged_at: "2026-08-09T10:00:00Z",
  triage_notes: "Back panel removed for access.",
  items: [
    {
      component_name: "Pump assembly",
      recommended_action: "harvest",
      condition: "damaged",
      repair_feasible: false,
      harvest_viable: true,
      source_required: null,
      notes: "Impeller cracked",
      replaceable: true,
      salvageable: true,
      consumable: false,
      part_number: "P-1042",
    },
    {
      component_name: "Control board",
      recommended_action: "assess",
      condition: "unknown",
      repair_feasible: null,
      harvest_viable: null,
      source_required: null,
      notes: null,
      replaceable: true,
      salvageable: false,
      consumable: false,
      part_number: "CB-7",
    },
  ],
  summary: {
    total_components: 2,
    needs_assessment: 1,
    repair_in_place: 0,
    harvest: 1,
    source_new: 0,
    no_action: 0,
    decommission: 0,
  },
  message: "Triage report generated",
};

export const salvageMatchItemFixture = {
  asset_id: ASSET_ID_B,
  asset_tag: "OHM-0043",
  manifest_id: "okh-0001",
  location: "Store room",
  component_name: "Pump assembly",
  condition: "intact",
  notes: null,
  assessed_by: "ana",
  observed_at: "2026-08-01T09:00:00Z",
  part_number: "P-1042",
  salvageable: true,
  replaceable: true,
  claimed_by: null,
  claimed_at: null,
};

export const salvageMatchFixture = {
  matches: [salvageMatchItemFixture],
  total: 1,
  query: {
    component_name: "Pump assembly",
    part_number: null,
    manifest_id: null,
  },
  message: "1 harvestable match(es) found",
};

export const sourcingResolutionFixture = {
  asset_id: ASSET_ID,
  asset_tag: "OHM-0042",
  manifest_id: "okh-0001",
  items: [
    {
      component_name: "Control board",
      verdict: "fleet_available",
      part_number: "CB-7",
      matches: [
        { ...salvageMatchItemFixture, component_name: "Control board" },
      ],
      match_count: 1,
    },
    {
      component_name: "Pump assembly",
      verdict: "procure_new",
      part_number: "P-1042",
      matches: [],
      match_count: 0,
    },
  ],
  total_components: 2,
  fleet_available_count: 1,
  procure_new_count: 1,
  message: "Sourcing resolved",
};

export const claimComponentFixture = {
  success: true,
  asset_id: ASSET_ID_B,
  component_name: "Pump assembly",
  claimed_by: "ana",
  claimed_at: "2026-08-12T09:00:00Z",
  message: "Component claimed",
};

export const llmHealthFixture = {
  status: "success",
  message: "LLM service healthy",
  health_status: "healthy",
  providers: {
    anthropic: {
      name: "anthropic",
      type: "anthropic",
      status: "healthy",
      model: "claude-sonnet-4-5-20250929",
      is_connected: true,
      available_models: ["claude-sonnet-4-5-20250929"],
      error: null,
    },
  },
  metrics: {},
};

export const llmProvidersFixture = {
  status: "success",
  message: "1 provider available",
  providers: [
    {
      name: "anthropic",
      type: "anthropic",
      status: "healthy",
      model: "claude-sonnet-4-5-20250929",
      is_connected: true,
      available_models: ["claude-sonnet-4-5-20250929"],
      error: null,
    },
  ],
  default_provider: "anthropic",
  available_providers: ["anthropic"],
};

export const fileTypesFixture = {
  status: "success",
  message: "File type taxonomy retrieved successfully",
  data: {
    total: 3,
    source: "config/file_types.yaml",
    file_types: [
      {
        canonical_id: "image.raster",
        display_name: "Raster image",
        parent: "image",
        extensions: ["png", "jpg"],
        mime_types: ["image/png"],
        okh_role: "documentation",
        render_tier: "native_inline",
      },
      {
        canonical_id: "cad.step",
        display_name: "STEP model",
        parent: "cad",
        // The point of the fixture: the client regex has never heard of .step,
        // so without the taxonomy this file falls to download_only.
        extensions: ["step", "stp"],
        mime_types: ["model/step"],
        okh_role: "design",
        render_tier: "wasm_3d",
      },
      {
        canonical_id: "doc.markdown",
        display_name: "Markdown",
        parent: "doc",
        extensions: ["md"],
        mime_types: ["text/markdown"],
        okh_role: "documentation",
        render_tier: "text_viewer",
      },
    ],
  },
};

const capabilityRule = {
  id: "cnc-milling-satisfies-machining",
  type: "capability",
  capability: "cnc_milling",
  satisfies_requirements: ["machining", "milling"],
  direction: "bidirectional",
  confidence: 0.9,
  domain: "manufacturing",
  description: "A 3-axis mill satisfies general machining requirements",
  source: "config/capability_rules.yaml",
  tags: ["subtractive"],
};

export const rulesListFixture = {
  status: "success",
  message: "Rules retrieved successfully",
  data: {
    rules: [capabilityRule],
    total: 1,
    domains: ["manufacturing"],
  },
};

export const rulesValidateFixture = {
  status: "success",
  message: "Validation completed",
  data: { valid: true, errors: [], warnings: [] },
};

export const rulesCompareFixture = {
  status: "success",
  message: "Comparison completed",
  data: {
    domains: {
      manufacturing: {
        changes: {
          added: ["laser-cutting"],
          updated: ["cnc-milling"],
          deleted: [],
        },
      },
    },
  },
};

export const rulesImportFixture = {
  status: "success",
  message: "Import completed",
  data: { imported: 2, domains: ["manufacturing"] },
};

export const rulesExportFixture = {
  status: "success",
  message: "Export completed",
  data: { file_content: "domain: manufacturing\nrules: []\n" },
};

export const taxonomyValidateFixture = {
  status: "success",
  message: "Taxonomy validation completed",
  data: {
    valid: true,
    total_processes: 51,
    errors: [],
    source: "config/processes.yaml",
  },
};

export const fileTypesValidationFixture = {
  status: "success",
  message: "File type taxonomy validation completed",
  data: {
    valid: true,
    total_file_types: 3,
    errors: [],
    source: "config/file_types.yaml",
  },
};

export const okhRequirementsFixture = {
  requirements: [
    { process_name: "3d_printing", quantity: 1 },
    { process_name: "assembly", quantity: 1 },
  ],
};

export const okwCapabilitiesFixture = {
  capabilities: [
    { process_name: "3d_printing" },
    { process_name: "cnc_machining" },
  ],
};

export const okhTemplateFixture = {
  title: "",
  version: "",
  function: "",
  license: { hardware: "", documentation: "", software: "" },
  licensor: { name: "" },
  documentation_language: "en",
};

export const okwTemplateFixture = {
  name: "",
  location: { address: {} },
  access_type: "",
  facility_status: "",
};

export const solutionStalenessFixture = {
  status: "success",
  message: "Staleness check completed",
  data: {
    solution_id: "sol-1",
    // Fresh by default: the banner is the exception, and a fixture that made
    // every mocked page shout would train readers to ignore it.
    is_stale: false,
    staleness_reason: null,
    age_days: 2,
  },
};

export const solutionHierarchyFixture = {
  status: "success",
  message: "Hierarchy retrieved",
  data: {
    // A list, as the API returns. Nothing in the app reads it yet, which is
    // exactly why it drifted to `{}` unnoticed.
    hierarchy: [],
    // Objects, not ids — matching the API. A fixture of bare strings is what
    // let a render of `{root}` pass its tests and throw React #31 for a user.
    root_components: [
      {
        component_id: "frame",
        component_name: "Frame",
        tree_id: "11111111-1111-1111-1111-111111111111",
      },
    ],
    component_details: { frame: { name: "Frame" } },
    summary: {
      total_components: 1,
      root_components: 1,
      total_trees: 1,
      max_depth: 1,
    },
  },
};

export const generateJobEventsFixture = {
  status: "success",
  message: "Events retrieved",
  data: {
    job_id: "job-1",
    state: "PROGRESS",
    next_cursor: 3,
    events: [
      {
        seq: 0,
        stage: "clone",
        fraction: 0.12,
        message: "Reading repository",
        ts: "2026-08-29T12:00:00+00:00",
      },
      {
        seq: 1,
        stage: "direct",
        fraction: 0.17,
        message: null,
        ts: "2026-08-29T12:00:04+00:00",
      },
      {
        seq: 2,
        stage: "nlp",
        fraction: 0.4,
        message: null,
        ts: "2026-08-29T12:00:04.200+00:00",
      },
    ],
  },
};

export const remotePackagesFixture = {
  status: "success",
  message: "Remote packages listed",
  data: {
    packages: [{ name: "demo/widget", version: "1.1.0" }],
    total: 1,
  },
};

export const packageSignatureFixture = {
  valid: true,
  signed_by: "did:key:z6MkDemo",
};

export const matchDomainsFixture = {
  status: "success",
  message: "Domains listed",
  data: {
    domains: [
      {
        // `id` and `name` are deliberately different strings. A fixture that
        // used the key for both made binding the selector to `name` look
        // correct while it sent an unmatchable value to the server.
        id: "manufacturing",
        name: "Manufacturing & Hardware Production",
        status: "available",
        version: "1.0",
        supported_input_types: ["okh"],
      },
      {
        id: "cooking",
        name: "Cooking & Food Preparation",
        status: "available",
        version: "0.1",
        supported_input_types: ["recipe"],
      },
    ],
  },
};

export const fixturesByPath: Record<string, unknown> = {
  "/v1/api/match/domains": matchDomainsFixture,
  "/v1/api/okh/generate-from-url/jobs/job-1/events": generateJobEventsFixture,
  "/v1/api/package/remote": remotePackagesFixture,
  "/v1/api/package/demo/widget/1.0.0/verify-signature": packageSignatureFixture,
  "/v1/api/supply-tree/solution/sol-1/staleness": solutionStalenessFixture,
  "/v1/api/supply-tree/solution/sol-1/hierarchy": solutionHierarchyFixture,
  "/v1/api/supply-tree/solution/sol-1/extend": {
    status: "success",
    message: "TTL extended successfully",
  },
  "/v1/api/okh/recipes": recipesFixture,
  "/v1/api/okw/kitchens": kitchensFixture,
  "/v1/api/okh/extract": okhRequirementsFixture,
  "/v1/api/okh/template": okhTemplateFixture,
  "/v1/api/okw/extract": okwCapabilitiesFixture,
  "/v1/api/okw/template": okwTemplateFixture,
  "/v1/api/match/rules": rulesListFixture,
  "/v1/api/match/rules/": rulesListFixture,
  "/v1/api/match/rules/validate": rulesValidateFixture,
  "/v1/api/match/rules/compare": rulesCompareFixture,
  "/v1/api/match/rules/import": rulesImportFixture,
  "/v1/api/match/rules/export": rulesExportFixture,
  "/v1/api/match/rules/reset": { status: "success", message: "Rules reset" },
  "/v1/api/taxonomy/validate": taxonomyValidateFixture,
  "/v1/api/taxonomy/reload": {
    status: "success",
    message: "Taxonomy reloaded",
    data: {
      added: [],
      removed: [],
      total: 51,
      source: "config/processes.yaml",
      version: "1.0.0",
    },
  },
  "/v1/api/file-types/validate": fileTypesValidationFixture,
  "/v1/api/file-types": fileTypesFixture,
  "/v1/api/asset": assetListFixture,
  "/v1/api/asset/": assetListFixture,
  [`/v1/api/asset/${ASSET_ID}`]: assetDetailFixture,
  [`/v1/api/asset/${ASSET_ID}/triage`]: assetDetailFixture,
  [`/v1/api/asset/${ASSET_ID}/triage-checklist`]: triageChecklistFixture,
  [`/v1/api/asset/${ASSET_ID}/triage-report`]: triageReportFixture,
  [`/v1/api/asset/${ASSET_ID}/resolve-sourcing`]: sourcingResolutionFixture,
  [`/v1/api/asset/${ASSET_ID_B}`]: assetListFixture.assets[1],
  [`/v1/api/asset/${ASSET_ID_B}/claim-component`]: claimComponentFixture,
  "/v1/api/asset/salvage-match": salvageMatchFixture,
  "/v1/api/supply-tree/solutions": solutionsListFixture,
  "/health": healthFixture,
  "/v1/api/utility/domains": domainsFixture,
  "/v1/api/utility/metrics": metricsFixture,
  "/v1/api/okh": okhListFixture,
  "/v1/api/okh/okh-0001": okhDetailFixture,
  "/v1/api/okh/validate": validationResultFixture,
  "/v1/api/okh/okh-0001/provenance": provenanceFixture,
  "/v1/api/okh/okh-0001/visibility": visibilityFixture,
  "/v1/api/okw/search": okwSearchFixture,
  "/v1/api/okw/okw-1": okwDetailFixture,
  "/v1/api/okw/validate": validationResultFixture,
  "/v1/api/taxonomy": taxonomyFixture,
  "/v1/api/okw/okw-1/provenance": provenanceFixture,
  "/v1/api/okw/okw-1/visibility": { ...visibilityFixture, id: "okw-1" },
  "/v1/api/okw/okw-1/disclosure": disclosureFixture,
  "/v1/api/okw/okw-1/disclosure/preview": disclosurePreviewFixture,
  "/v1/api/match": matchResponseFixture,
  "/v1/api/match/facility": facilityDesignsFixture,
  "/v1/api/okw/spaces": networkSpacesFixture,
  "/v1/api/supply-tree/solution/sol-1/visualization": vizBundleFixture,
  "/v1/api/identity/whoami": whoamiAdminFixture,
  "/v1/api/identity/security-policy": securityPolicyFixture,
  "/v1/api/identity/keys": apiKeysFixture,
  "/v1/api/identity/accounts": accountsFixture,
  "/v1/api/identity/spaces": spaceClaimsFixture,
  "/v1/api/identity/grants": grantsFixture,
  "/v1/api/identity/attestations": attestationsFixture,
  "/v1/api/identity/bindings": bindingsFixture,
  "/v1/api/identity/directory": directoryFixture,
  "/v1/api/identity/identities": identitiesFixture,
  "/v1/api/llm/credentials": llmCredentialsFixture,
  "/v1/api/llm/health": llmHealthFixture,
  "/v1/api/llm/providers": llmProvidersFixture,
  "/v1/api/federation/status": federationStatusFixture,
  "/v1/api/federation/peers": federationPeersFixture,
  "/v1/api/package/list": packageListFixture,
  "/v1/api/package/demo/widget/1.0.0": packageMetadataFixture,
};
