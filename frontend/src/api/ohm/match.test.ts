import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { ApiError } from "./client";
import { runMatch } from "./match";

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

  it("throws ApiError on failure", async () => {
    server.use(
      http.post("*/v1/api/match", () =>
        HttpResponse.json({ message: "boom" }, { status: 500 }),
      ),
    );
    await expect(runMatch({ okhId: "x" })).rejects.toBeInstanceOf(ApiError);
  });
});
