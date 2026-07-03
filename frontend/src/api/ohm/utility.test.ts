import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { ApiError } from "./client";
import { fetchDomains, fetchMetrics } from "./utility";

describe("fetchDomains", () => {
  it("narrows data.domains to Domain[]", async () => {
    const domains = await fetchDomains();
    expect(domains.map((d) => d.id)).toContain("manufacturing");
    expect(domains[0]).toHaveProperty("name");
  });

  it("throws ApiError on failure", async () => {
    server.use(
      http.get("*/v1/api/utility/domains", () => HttpResponse.json({}, { status: 500 })),
    );
    await expect(fetchDomains()).rejects.toBeInstanceOf(ApiError);
  });
});

describe("fetchMetrics", () => {
  it("flattens error_summary.total_errors and request counts", async () => {
    const m = await fetchMetrics();
    expect(m.total_errors).toBe(0);
    expect(m.recent_requests_1h).toBe(111);
  });
});
