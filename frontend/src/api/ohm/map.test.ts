import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { ApiError } from "./client";
import { fetchMapPoints } from "./map";

describe("fetchMapPoints", () => {
  it("returns source-labeled points and counts from the flat envelope", async () => {
    const res = await fetchMapPoints();
    expect(res.local_count).toBe(2);
    expect(res.mom_count).toBe(1);
    expect(res.mom_available).toBe(true);
    expect(res.points.map((p) => p.source)).toContain("mom");
  });

  it("passes include_mom=false through the query string", async () => {
    let url = "";
    server.use(
      http.get("*/v1/api/okw/spaces", ({ request }) => {
        url = request.url;
        return HttpResponse.json({ spaces: [], local_count: 0, mom_count: 0, dropped_no_coords: 0, mom_available: false });
      }),
    );
    await fetchMapPoints(false);
    expect(url).toContain("include_mom=false");
  });

  it("throws ApiError on failure", async () => {
    server.use(
      http.get("*/v1/api/okw/spaces", () => HttpResponse.json({ detail: "boom" }, { status: 500 })),
    );
    await expect(fetchMapPoints()).rejects.toBeInstanceOf(ApiError);
  });
});
