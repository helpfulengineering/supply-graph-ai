import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../../test/msw/server";
import {
  fetchProcessTaxonomy,
  reloadProcessTaxonomy,
  validateProcessTaxonomy,
} from "./taxonomy";

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

  it("names the endpoint and field when the shape drifts", async () => {
    // The process list feeds a form's options, so a drift degrades to a form
    // with nothing to choose. The parse turns that into a stated failure.
    server.use(
      http.get("*/v1/api/taxonomy", () =>
        HttpResponse.json({ data: { processes: [{ canonical_id: 1 }] } }),
      ),
    );
    await expect(fetchProcessTaxonomy()).rejects.toThrow(
      /\/api\/taxonomy.*processes\.0/,
    );
  });
});

describe("reloadProcessTaxonomy", () => {
  it("reports the process count the route actually returns", async () => {
    // Regression: this read `total_processes`, which reload has never sent —
    // the field is `total`, and `total_processes` belongs to validate. The
    // settings panel therefore said "Reloaded 0 process(es)" every time, and
    // the fixture encoded the same wrong name so the suite agreed.
    expect(await reloadProcessTaxonomy()).toBe(51);
  });
});

describe("validateProcessTaxonomy", () => {
  it("returns the validation payload, which does carry total_processes", async () => {
    // The near-identical naming across the two routes is how the reload bug
    // survived; pinning both keeps them told apart.
    const result = await validateProcessTaxonomy();
    expect(result.valid).toBe(true);
    expect(result.total_processes).toBe(51);
  });
});
