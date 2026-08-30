import { http, HttpResponse } from "msw";
import {
  domainsFixture,
  generateJobEventsFixture,
  healthFixture,
  metricsFixture,
  matchResponseFixture,
  facilityDesignsFixture,
  networkSpacesFixture,
  vizBundleFixture,
  okhDetailFixture,
  okhListFixture,
  okwDetailFixture,
  okwSearchFixture,
  validationResultFixture,
  whoamiAdminFixture,
  securityPolicyFixture,
  apiKeysFixture,
  accountsFixture,
  identityFixture,
  registrationFixture,
  grantsFixture,
  spaceClaimsFixture,
  attestationsFixture,
  pinRecordFixture,
  bindingsFixture,
  domainBindStartFixture,
  directoryFixture,
  federationStatusFixture,
  federationPeersFixture,
  federationSyncFixture,
  provenanceFixture,
  visibilityFixture,
  disclosureFixture,
  disclosurePreviewFixture,
  fileTypesFixture,
  fileTypesValidationFixture,
  okhRequirementsFixture,
  okhTemplateFixture,
  okwCapabilitiesFixture,
  okwTemplateFixture,
  rulesCompareFixture,
  solutionHierarchyFixture,
  solutionStalenessFixture,
  rulesExportFixture,
  rulesImportFixture,
  rulesListFixture,
  rulesValidateFixture,
  taxonomyValidateFixture,
  llmCredentialsFixture,
  llmHealthFixture,
  llmProvidersFixture,
  matchDomainsFixture,
  packageListFixture,
  packageSignatureFixture,
  remotePackagesFixture,
  packageMetadataFixture,
  taxonomyFixture,
} from "../fixtures";

// MSW handlers for vitest (node) unit/component tests. These mirror the
// Playwright mocked-lane interceptor; both draw on src/test/fixtures.
export const handlers = [
  // Before the generic */health below: that pattern's leading wildcard also
  // matches /v1/api/llm/health, so the node's liveness fixture would answer
  // the LLM service's health check.
  // Before the "*/v1/api/okh/:id" rule below, whose param would swallow
  // "extract" and "template" as ids.
  http.post("*/v1/api/okh/extract", () =>
    HttpResponse.json(okhRequirementsFixture),
  ),
  http.get("*/v1/api/okh/template", () =>
    HttpResponse.json(okhTemplateFixture),
  ),
  http.post("*/v1/api/okw/extract", () =>
    HttpResponse.json(okwCapabilitiesFixture),
  ),
  http.get("*/v1/api/okw/template", () =>
    HttpResponse.json(okwTemplateFixture),
  ),
  http.get("*/v1/api/supply-tree/solution/:id/staleness", () =>
    HttpResponse.json(solutionStalenessFixture),
  ),
  http.get("*/v1/api/supply-tree/solution/:id/hierarchy", () =>
    HttpResponse.json(solutionHierarchyFixture),
  ),
  http.post("*/v1/api/supply-tree/solution/:id/extend", () =>
    HttpResponse.json({ status: "success", message: "TTL extended" }),
  ),
  http.get("*/v1/api/file-types/validate", () =>
    HttpResponse.json(fileTypesValidationFixture),
  ),
  http.get("*/v1/api/file-types", () => HttpResponse.json(fileTypesFixture)),
  http.get("*/v1/api/okh/generate-from-url/jobs/:id/events", () =>
    HttpResponse.json(generateJobEventsFixture),
  ),
  http.get("*/v1/api/match/domains", () =>
    HttpResponse.json(matchDomainsFixture),
  ),
  http.get("*/v1/api/match/rules/", () => HttpResponse.json(rulesListFixture)),
  http.post("*/v1/api/match/rules/validate", () =>
    HttpResponse.json(rulesValidateFixture),
  ),
  http.post("*/v1/api/match/rules/compare", () =>
    HttpResponse.json(rulesCompareFixture),
  ),
  http.post("*/v1/api/match/rules/import", () =>
    HttpResponse.json(rulesImportFixture),
  ),
  http.post("*/v1/api/match/rules/export", () =>
    HttpResponse.json(rulesExportFixture),
  ),
  http.post("*/v1/api/match/rules/reset", () =>
    HttpResponse.json({ status: "success", message: "Rules reset" }),
  ),
  http.get("*/v1/api/taxonomy/validate", () =>
    HttpResponse.json(taxonomyValidateFixture),
  ),
  http.post("*/v1/api/taxonomy/reload", () =>
    HttpResponse.json({
      status: "success",
      message: "Taxonomy reloaded",
      data: {
        // The shape the route actually returns — the golden in
        // tests/api/golden/taxonomy_reload.json is the source of truth. This
        // said `total_processes`, matching a field the client read and the API
        // has never sent, so the suite was green against a payload that does
        // not exist.
        added: [],
        removed: [],
        total: 51,
        source: "config/processes.yaml",
        version: "1.0.0",
      },
    }),
  ),
  http.get("*/v1/api/llm/health", () => HttpResponse.json(llmHealthFixture)),
  http.get("*/v1/api/llm/providers", () =>
    HttpResponse.json(llmProvidersFixture),
  ),
  http.get("*/v1/api/llm/credentials", () =>
    HttpResponse.json(llmCredentialsFixture),
  ),
  http.get("*/health", () => HttpResponse.json(healthFixture)),
  http.get("*/v1/api/utility/domains", () => HttpResponse.json(domainsFixture)),
  http.get("*/v1/api/utility/metrics", () => HttpResponse.json(metricsFixture)),
  http.get("*/v1/api/okh", () => HttpResponse.json(okhListFixture)),
  http.get("*/v1/api/okh/:id/provenance", () =>
    HttpResponse.json(provenanceFixture),
  ),
  http.get("*/v1/api/okh/:id/visibility", () =>
    HttpResponse.json(visibilityFixture),
  ),
  http.put("*/v1/api/okh/:id/visibility", async ({ request }) => {
    const body = (await request.json()) as { visibility?: string };
    return HttpResponse.json({
      id: "00000000-0000-0000-0000-000000000001",
      visibility: body.visibility ?? "private",
    });
  }),
  http.get("*/v1/api/okh/:id", () => HttpResponse.json(okhDetailFixture)),
  http.post("*/v1/api/okh/validate", () =>
    HttpResponse.json(validationResultFixture),
  ),
  http.post("*/v1/api/okh/create", () =>
    HttpResponse.json(
      {
        success: true,
        message: "created",
        okh: { ...okhDetailFixture, id: "okh-created" },
      },
      { status: 201 },
    ),
  ),
  http.post("*/v1/api/okh/generate-from-url/jobs", async ({ request }) => {
    const body = (await request.json()) as { urls?: string[] };
    const urls = body.urls ?? ["https://github.com/example/demo"];
    return HttpResponse.json(
      {
        batch_id: "batch-msw",
        jobs: urls.map((url, i) => ({ job_id: `job-msw-${i}`, url })),
      },
      { status: 202 },
    );
  }),
  http.get("*/v1/api/okh/generate-from-url/jobs/:jobId", ({ params }) =>
    HttpResponse.json({
      job_id: String(params.jobId),
      state: "SUCCESS",
      fraction: 1,
      message: "ok",
      url: "https://github.com/example/demo",
      manifest: okhDetailFixture,
      quality_report: { missing_required_fields: [], recommendations: [] },
    }),
  ),
  http.post("*/v1/api/okh/generate-from-url/jobs/:jobId/revoke", ({ params }) =>
    HttpResponse.json({
      job_id: String(params.jobId),
      state: "REVOKED",
      message: "Job cancelled",
    }),
  ),
  http.get("*/v1/api/okw/search", () => HttpResponse.json(okwSearchFixture)),
  http.get("*/v1/api/okw/spaces", () =>
    HttpResponse.json(networkSpacesFixture),
  ),
  http.get("*/v1/api/okw/:id/provenance", () =>
    HttpResponse.json(provenanceFixture),
  ),
  http.get("*/v1/api/okw/:id/visibility", () =>
    HttpResponse.json({ ...visibilityFixture, id: "okw-1" }),
  ),
  http.put("*/v1/api/okw/:id/visibility", async ({ request }) => {
    const body = (await request.json()) as { visibility?: string };
    return HttpResponse.json({
      id: "okw-1",
      visibility: body.visibility ?? "private",
    });
  }),
  http.get("*/v1/api/okw/:id/disclosure/preview", () =>
    HttpResponse.json(disclosurePreviewFixture),
  ),
  http.get("*/v1/api/okw/:id/disclosure", () =>
    HttpResponse.json(disclosureFixture),
  ),
  http.put("*/v1/api/okw/:id/disclosure", async ({ request }) => {
    const body = (await request.json()) as {
      followers?: { groups?: string[] };
      public?: { groups?: string[] };
    };
    return HttpResponse.json({
      id: "okw-1",
      disclosure: {
        followers: body.followers ?? disclosureFixture.disclosure.followers,
        public: body.public ?? disclosureFixture.disclosure.public,
      },
    });
  }),
  http.get("*/v1/api/okw/:id", () => HttpResponse.json(okwDetailFixture)),
  http.post("*/v1/api/okw/validate", () =>
    HttpResponse.json(validationResultFixture),
  ),
  http.post("*/v1/api/okw/create", () =>
    HttpResponse.json(
      {
        success: true,
        message: "created",
        okw: { ...okwDetailFixture, id: "okw-created" },
      },
      { status: 201 },
    ),
  ),
  http.put("*/v1/api/okw/:id", async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      ...okwDetailFixture,
      id: String(params.id),
      ...body,
    });
  }),
  http.delete("*/v1/api/okw/:id", () =>
    HttpResponse.json({ success: true, message: "deleted" }),
  ),
  http.get("*/v1/api/taxonomy", () => HttpResponse.json(taxonomyFixture)),
  http.post("*/v1/api/match/facility", () =>
    HttpResponse.json(facilityDesignsFixture),
  ),
  http.post("*/v1/api/match", () => HttpResponse.json(matchResponseFixture)),
  http.get("*/v1/api/supply-tree/solution/:id/visualization", () =>
    HttpResponse.json(vizBundleFixture),
  ),
  http.get("*/v1/api/identity/whoami", () =>
    HttpResponse.json(whoamiAdminFixture),
  ),
  http.get("*/v1/api/identity/security-policy", () =>
    HttpResponse.json(securityPolicyFixture),
  ),
  http.post("*/v1/api/identity/register", () =>
    HttpResponse.json(registrationFixture, { status: 201 }),
  ),
  http.get("*/v1/api/identity/keys", () => HttpResponse.json(apiKeysFixture)),
  http.get("*/v1/api/identity/accounts", () =>
    HttpResponse.json(accountsFixture),
  ),
  http.post("*/v1/api/identity/identities", () =>
    HttpResponse.json(identityFixture, { status: 201 }),
  ),
  http.get("*/v1/api/identity/identities/:did", () =>
    HttpResponse.json(identityFixture),
  ),
  http.post("*/v1/api/identity/identities/:did/rotate", () =>
    HttpResponse.json({
      ...identityFixture,
      did: "did:key:z6MktestPersonRotated0000000000000001",
    }),
  ),
  http.get("*/v1/api/identity/grants", () => HttpResponse.json(grantsFixture)),
  http.post("*/v1/api/identity/grants", () =>
    HttpResponse.json(grantsFixture[0], { status: 201 }),
  ),
  http.delete("*/v1/api/identity/grants/:grant_id", () =>
    HttpResponse.json({ success: true, message: "revoked" }),
  ),
  http.post("*/v1/api/identity/grants/bootstrap-edge", () =>
    HttpResponse.json(grantsFixture[0], { status: 201 }),
  ),
  http.get("*/v1/api/identity/spaces", () =>
    HttpResponse.json(spaceClaimsFixture),
  ),
  http.post("*/v1/api/identity/spaces/claim", () =>
    HttpResponse.json(spaceClaimsFixture[0], { status: 201 }),
  ),
  http.get("*/v1/api/identity/attestations", () =>
    HttpResponse.json(attestationsFixture),
  ),
  http.post("*/v1/api/identity/attestations/certify", () =>
    HttpResponse.json(attestationsFixture[0], { status: 201 }),
  ),
  http.get("*/v1/api/identity/reputation/:did", () =>
    HttpResponse.json(attestationsFixture),
  ),
  http.get("*/v1/api/identity/bindings", () =>
    HttpResponse.json(bindingsFixture),
  ),
  http.post("*/v1/api/identity/bindings/domain/verify", () =>
    HttpResponse.json({
      ...domainBindStartFixture.binding,
      verified: true,
      challenge: null,
      verified_at: "2026-01-02T00:00:00Z",
    }),
  ),
  http.post("*/v1/api/identity/bindings/domain", () =>
    HttpResponse.json(domainBindStartFixture, { status: 201 }),
  ),
  http.post("*/v1/api/identity/bindings/oauth", () =>
    HttpResponse.json(bindingsFixture[0], { status: 201 }),
  ),
  http.get("*/v1/api/identity/directory", () =>
    HttpResponse.json(directoryFixture),
  ),
  http.post("*/v1/api/identity/directory", () =>
    HttpResponse.json(directoryFixture[0], { status: 201 }),
  ),
  http.get("*/v1/api/federation/status", () =>
    HttpResponse.json(federationStatusFixture),
  ),
  http.get("*/v1/api/federation/peers", () =>
    HttpResponse.json(federationPeersFixture),
  ),
  http.post("*/v1/api/federation/peers/discover", () =>
    HttpResponse.json({
      updated: federationPeersFixture.peers,
      peers: federationPeersFixture.peers,
      total: federationPeersFixture.total,
    }),
  ),
  http.post("*/v1/api/federation/peers/:did/follow", () =>
    HttpResponse.json({
      did: federationPeersFixture.peers[0]!.did,
      followed: true,
    }),
  ),
  http.delete("*/v1/api/federation/peers/:did/follow", () =>
    HttpResponse.json({
      did: federationPeersFixture.peers[0]!.did,
      followed: false,
    }),
  ),
  http.post("*/v1/api/federation/sync/run", () =>
    HttpResponse.json(federationSyncFixture),
  ),
  http.post("*/v1/api/federation/okw/sync/run", () =>
    HttpResponse.json(federationSyncFixture),
  ),
  http.post("*/v1/api/package/:org/:project/:version/pin", () =>
    HttpResponse.json({
      status: "success",
      message: "pinned",
      data: { pin_record: pinRecordFixture },
    }),
  ),
  // Before the ":org/:project/:version" rule, which would read "remote" as an
  // org.
  http.get("*/v1/api/package/remote", () =>
    HttpResponse.json(remotePackagesFixture),
  ),
  http.get("*/v1/api/package/:org/:project/:version/verify-signature", () =>
    HttpResponse.json(packageSignatureFixture),
  ),
  http.get("*/v1/api/package/list", () =>
    HttpResponse.json(packageListFixture),
  ),
  http.get("*/v1/api/package/:org/:project/:version", () =>
    HttpResponse.json(packageMetadataFixture),
  ),
];
