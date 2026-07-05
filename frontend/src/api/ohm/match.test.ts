import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { ApiError } from "./client";
import { runMatch, fetchDesignsForFacility } from "./match";

describe("runMatch", () => {
  it("posts okh_id and returns the raw envelope", async () => {
    let body: { okh_id?: string } | null = null;
    server.use(
      http.post("*/v1/api/match", async ({ request }) => {
        body = (await request.json()) as { okh_id?: string };
        return HttpResponse.json({ data: { solutions: [] } });
      }),
    );
    const res = await runMatch({ okhId: "okh-1" });
    expect(body!.okh_id).toBe("okh-1");
    expect(res.data?.solutions).toEqual([]);
  });

  it("sends network_filter for a network match", async () => {
    let body: { network_filter?: Record<string, unknown>; okw_ids?: unknown } | null = null;
    server.use(
      http.post("*/v1/api/match", async ({ request }) => {
        body = (await request.json()) as { network_filter?: Record<string, unknown> };
        return HttpResponse.json({ data: { solutions: [] } });
      }),
    );
    await runMatch({ okhId: "okh-1", okwIds: ["a"], networkFilter: { country: "FR", include_mom: true } });
    expect(body!.network_filter).toEqual({ country: "FR", include_mom: true });
    expect(body!.okw_ids).toBeUndefined(); // network filter supersedes the subset
  });

  it("throws ApiError on failure", async () => {
    server.use(
      http.post("*/v1/api/match", () =>
        HttpResponse.json({ message: "boom" }, { status: 500 }),
      ),
    );
    await expect(runMatch({ okhId: "x" })).rejects.toBeInstanceOf(ApiError);
  });
});

describe("fetchDesignsForFacility", () => {
  it("posts okw_id and narrows the data envelope to ranked designs", async () => {
    let body: { okw_id?: string; min_confidence?: number } | null = null;
    server.use(
      http.post("*/v1/api/match/facility", async ({ request }) => {
        body = (await request.json()) as { okw_id?: string; min_confidence?: number };
        return HttpResponse.json({
          data: {
            facility_name: "Laser Fab Lab",
            designs: [{ okh_id: "okh-0001", okh_title: "Open Ventilator", confidence: 0.9, rank: 1 }],
            total_designs: 1,
          },
        });
      }),
    );
    const res = await fetchDesignsForFacility("okw-1");
    expect(body!.okw_id).toBe("okw-1");
    expect(body!.min_confidence).toBe(0.1);
    expect(res.facility_name).toBe("Laser Fab Lab");
    expect(res.designs.map((d) => d.okh_title)).toContain("Open Ventilator");
  });

  it("throws ApiError on failure", async () => {
    server.use(
      http.post("*/v1/api/match/facility", () =>
        HttpResponse.json({ detail: "nope" }, { status: 404 }),
      ),
    );
    await expect(fetchDesignsForFacility("missing")).rejects.toBeInstanceOf(ApiError);
  });
});
