import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { ApiError } from "./client";
import { fetchOkhList } from "./okh";

describe("fetchOkhList", () => {
  it("returns narrowed items and pagination from the paginated envelope", async () => {
    const result = await fetchOkhList();
    expect(result.items).toHaveLength(3);
    expect(result.items.map((i) => i.title)).toContain("Open Ventilator");
    expect(result.pagination.total_items).toBe(3);
  });

  it("passes paging/sort/filter as query params", async () => {
    let captured: URLSearchParams | null = null;
    server.use(
      http.get("*/v1/api/okh", ({ request }) => {
        captured = new URL(request.url).searchParams;
        return HttpResponse.json({ items: [], pagination: { total_items: 0 } });
      }),
    );
    await fetchOkhList({ page: 2, page_size: 10, sort_by: "title", sort_order: "asc", filter: "vent" });
    expect(captured!.get("page")).toBe("2");
    expect(captured!.get("page_size")).toBe("10");
    expect(captured!.get("sort_by")).toBe("title");
    expect(captured!.get("filter")).toBe("vent");
  });

  it("throws ApiError with the HTTP status on failure", async () => {
    server.use(
      http.get("*/v1/api/okh", () =>
        HttpResponse.json({ message: "boom" }, { status: 503 }),
      ),
    );
    await expect(fetchOkhList()).rejects.toMatchObject({
      name: "ApiError",
      status: 503,
    });
    await expect(fetchOkhList()).rejects.toBeInstanceOf(ApiError);
  });
});
