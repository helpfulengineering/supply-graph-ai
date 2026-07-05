import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { ApiError } from "./client";
import { fetchNetworkSpaces } from "./network";

describe("fetchNetworkSpaces", () => {
  it("returns the unified spaces + counts from the flat envelope", async () => {
    const res = await fetchNetworkSpaces();
    expect(res.local_count).toBe(2);
    expect(res.mom_count).toBe(1);
    expect(res.spaces.map((s) => s.source)).toContain("mom");
  });

  it("passes cross-source filters as query params", async () => {
    let url = "";
    server.use(
      http.get("*/v1/api/okw/spaces", ({ request }) => {
        url = request.url;
        return HttpResponse.json({ spaces: [], total: 0, local_count: 0, mom_count: 0, dropped_no_coords: 0, mom_available: true });
      }),
    );
    await fetchNetworkSpaces({ country: "FR", process: "laser_cutting" });
    expect(url).toContain("country=FR");
    expect(url).toContain("process=laser_cutting");
  });

  it("source=local skips MoM via include_mom=false", async () => {
    let url = "";
    server.use(
      http.get("*/v1/api/okw/spaces", ({ request }) => {
        url = request.url;
        return HttpResponse.json({ spaces: [], total: 0, local_count: 0, mom_count: 0, dropped_no_coords: 0, mom_available: false });
      }),
    );
    await fetchNetworkSpaces({ source: "local" });
    expect(url).toContain("include_mom=false");
  });

  it("throws ApiError on failure", async () => {
    server.use(
      http.get("*/v1/api/okw/spaces", () => HttpResponse.json({ detail: "boom" }, { status: 500 })),
    );
    await expect(fetchNetworkSpaces()).rejects.toBeInstanceOf(ApiError);
  });
});
