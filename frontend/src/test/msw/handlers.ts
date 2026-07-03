import { http, HttpResponse } from "msw";
import {
  domainsFixture,
  healthFixture,
  okhDetailFixture,
  okhListFixture,
  validationResultFixture,
} from "../fixtures";

// MSW handlers for vitest (node) unit/component tests. These mirror the
// Playwright mocked-lane interceptor; both draw on src/test/fixtures.
export const handlers = [
  http.get("*/health", () => HttpResponse.json(healthFixture)),
  http.get("*/v1/api/utility/domains", () => HttpResponse.json(domainsFixture)),
  http.get("*/v1/api/okh", () => HttpResponse.json(okhListFixture)),
  http.get("*/v1/api/okh/:id", () => HttpResponse.json(okhDetailFixture)),
  http.post("*/v1/api/okh/validate", () => HttpResponse.json(validationResultFixture)),
];
