import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { ApiError } from "./client";
import { fetchAllOkhList, fetchOkhList } from "./okh";

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

describe("fetchAllOkhList", () => {
  it("merges multiple pages and requests each page once", async () => {
    const pagesRequested: number[] = [];
    const page1 = Array.from({ length: 100 }, (_, i) => ({
      id: `okh-p1-${i}`,
      title: `Design ${i}`,
      licensor: { name: "A", email: null, affiliation: null, social: [] },
      manufacturing_processes: [],
      materials: [],
      keywords: [],
      contributors: [],
      design_files: [],
      manufacturing_files: [],
      making_instructions: [],
      parts: [],
      tool_list: [],
    }));
    const page2 = Array.from({ length: 50 }, (_, i) => ({
      id: `okh-p2-${i}`,
      title: `Design extra ${i}`,
      licensor: { name: "B", email: null, affiliation: null, social: [] },
      manufacturing_processes: [],
      materials: [],
      keywords: [],
      contributors: [],
      design_files: [],
      manufacturing_files: [],
      making_instructions: [],
      parts: [],
      tool_list: [],
    }));

    server.use(
      http.get("*/v1/api/okh", ({ request }) => {
        const page = Number(new URL(request.url).searchParams.get("page") ?? "1");
        pagesRequested.push(page);
        if (page === 1) {
          return HttpResponse.json({
            items: page1,
            pagination: {
              page: 1,
              page_size: 100,
              total_items: 150,
              total_pages: 2,
              has_next: true,
              has_previous: false,
            },
          });
        }
        return HttpResponse.json({
          items: page2,
          pagination: {
            page: 2,
            page_size: 100,
            total_items: 150,
            total_pages: 2,
            has_next: false,
            has_previous: true,
          },
        });
      }),
    );

    const result = await fetchAllOkhList();
    expect(pagesRequested).toEqual([1, 2]);
    expect(result.items).toHaveLength(150);
    expect(result.pagination.has_next).toBe(false);
    expect(result.pagination.total_items).toBe(150);
  });
});
