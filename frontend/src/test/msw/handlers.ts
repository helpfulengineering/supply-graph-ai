import { http, HttpResponse } from "msw";
import {
  domainsFixture,
  healthFixture,
  metricsFixture,
  matchResponseFixture,
  solutionsListFixture,
  vizBundleFixture,
  okhDetailFixture,
  okhListFixture,
  okwDetailFixture,
  okwSearchFixture,
  validationResultFixture,
} from "../fixtures";

// MSW handlers for vitest (node) unit/component tests. These mirror the
// Playwright mocked-lane interceptor; both draw on src/test/fixtures.
export const handlers = [
  http.get("*/health", () => HttpResponse.json(healthFixture)),
  http.get("*/v1/api/utility/domains", () => HttpResponse.json(domainsFixture)),
  http.get("*/v1/api/utility/metrics", () => HttpResponse.json(metricsFixture)),
  http.get("*/v1/api/okh", () => HttpResponse.json(okhListFixture)),
  http.get("*/v1/api/okh/:id", () => HttpResponse.json(okhDetailFixture)),
  http.post("*/v1/api/okh/validate", () => HttpResponse.json(validationResultFixture)),
  http.get("*/v1/api/okw/search", () => HttpResponse.json(okwSearchFixture)),
  http.get("*/v1/api/okw/:id", () => HttpResponse.json(okwDetailFixture)),
  http.post("*/v1/api/okw/validate", () => HttpResponse.json(validationResultFixture)),
  http.post("*/v1/api/match", () => HttpResponse.json(matchResponseFixture)),
  http.get("*/v1/api/supply-tree/solutions", () => HttpResponse.json(solutionsListFixture)),
  http.get("*/v1/api/supply-tree/solution/:id/visualization", () =>
    HttpResponse.json(vizBundleFixture),
  ),
];
