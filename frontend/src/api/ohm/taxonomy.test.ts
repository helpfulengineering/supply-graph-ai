import { describe, expect, it } from "vitest";
import { fetchProcessTaxonomy } from "./taxonomy";

describe("fetchProcessTaxonomy", () => {
  it("unwraps SuccessResponse data.processes", async () => {
    const processes = await fetchProcessTaxonomy();
    expect(processes.length).toBeGreaterThan(0);
    expect(processes[0]).toMatchObject({
      canonical_id: expect.any(String),
      display_name: expect.any(String),
      children: expect.any(Array),
    });
    expect(processes.some((p) => p.canonical_id === "3d_printing")).toBe(true);
  });
});
