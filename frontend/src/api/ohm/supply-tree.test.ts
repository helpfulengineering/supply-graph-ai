import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { ApiError } from "./client";
import { listSolutions } from "./supply-tree";

describe("listSolutions", () => {
  it("narrows the data.result envelope to solution summaries", async () => {
    const solutions = await listSolutions();
    expect(solutions).toHaveLength(2);
    expect(solutions.map((s) => s.okh_title)).toContain("Open Ventilator");
    expect(solutions[0].facility_name).toBe("FabLab Drome");
    expect(solutions[0].facility_count).toBe(2);
  });

  it("throws ApiError on failure", async () => {
    server.use(
      http.get("*/v1/api/supply-tree/solutions", () =>
        HttpResponse.json({ message: "boom" }, { status: 500 }),
      ),
    );
    await expect(listSolutions()).rejects.toBeInstanceOf(ApiError);
  });
});
