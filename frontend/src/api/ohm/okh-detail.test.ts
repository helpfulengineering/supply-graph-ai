import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { ApiError } from "./client";
import { fetchOkhDetail, validateOkh } from "./okh";

describe("fetchOkhDetail", () => {
  it("returns the manifest for an id", async () => {
    const okh = await fetchOkhDetail("okh-0001");
    expect(okh.title).toBe("Open Ventilator");
  });

  it("throws ApiError on failure", async () => {
    server.use(
      http.get("*/v1/api/okh/:id", () =>
        HttpResponse.json({ message: "not found" }, { status: 404 }),
      ),
    );
    await expect(fetchOkhDetail("missing")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
    });
    await expect(fetchOkhDetail("missing")).rejects.toBeInstanceOf(ApiError);
  });
});

describe("validateOkh", () => {
  it("returns a validation result", async () => {
    const res = await validateOkh({ title: "x" });
    expect(res.is_valid).toBe(true);
    expect(res.score).toBeCloseTo(0.92);
  });

  it("posts content in the body and quality/strict as query params", async () => {
    let body: { content?: { title?: string } } | null = null;
    let q: URLSearchParams | null = null;
    server.use(
      http.post("*/v1/api/okh/validate", async ({ request }) => {
        body = (await request.json()) as { content?: { title?: string } };
        q = new URL(request.url).searchParams;
        return HttpResponse.json({ is_valid: true, score: 1 });
      }),
    );
    await validateOkh(
      { title: "Widget" },
      { qualityLevel: "professional", strictMode: true },
    );
    expect(body!.content!.title).toBe("Widget");
    expect(q!.get("quality_level")).toBe("professional");
    expect(q!.get("strict_mode")).toBe("true");
  });
});
