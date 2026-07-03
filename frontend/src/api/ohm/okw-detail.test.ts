import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { ApiError } from "./client";
import { fetchOkwDetail, validateOkw } from "./okw";

describe("fetchOkwDetail", () => {
  it("returns the facility for an id", async () => {
    const f = await fetchOkwDetail("okw-1");
    expect(f.name).toBe("Laser Fab Lab");
    expect(f.equipment?.length).toBeGreaterThan(0);
  });

  it("throws ApiError on failure", async () => {
    server.use(
      http.get("*/v1/api/okw/:id", () =>
        HttpResponse.json({ message: "not found" }, { status: 404 }),
      ),
    );
    await expect(fetchOkwDetail("missing")).rejects.toBeInstanceOf(ApiError);
  });
});

describe("validateOkw", () => {
  it("posts content and returns a validation result", async () => {
    let body: { content?: unknown } | null = null;
    server.use(
      http.post("*/v1/api/okw/validate", async ({ request }) => {
        body = (await request.json()) as { content?: unknown };
        return HttpResponse.json({ is_valid: true, score: 1 });
      }),
    );
    const res = await validateOkw({ name: "X" });
    expect(res.is_valid).toBe(true);
    expect(body!.content).toEqual({ name: "X" });
  });
});
