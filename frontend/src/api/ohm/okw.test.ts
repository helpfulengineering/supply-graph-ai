import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { ApiError } from "./client";
import { searchOkw } from "./okw";

describe("searchOkw", () => {
  it("narrows the {results,total} envelope to facilities", async () => {
    const res = await searchOkw();
    expect(res.results).toHaveLength(3);
    expect(res.total).toBe(3);
    expect(res.results.map((f) => f.name)).toContain("Laser Fab Lab");
  });

  it("throws ApiError on failure", async () => {
    server.use(
      http.get("*/v1/api/okw/search", () =>
        HttpResponse.json({ message: "boom" }, { status: 500 }),
      ),
    );
    await expect(searchOkw()).rejects.toMatchObject({ name: "ApiError", status: 500 });
    await expect(searchOkw()).rejects.toBeInstanceOf(ApiError);
  });
});
