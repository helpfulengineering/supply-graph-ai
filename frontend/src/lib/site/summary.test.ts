import { describe, expect, it } from "vitest";
import { summarize } from "./summary";
import type { ActivityEntry } from "./rows";

function entry(overrides: Partial<ActivityEntry> = {}): ActivityEntry {
  return {
    ts: "2026-08-11T09:00:00.000Z",
    event: "page_view",
    page: "/match",
    sessionId: "sess-1",
    visitor: "ada@example.org",
    props: null,
    masked: false,
    ...overrides,
  };
}

describe("summarize", () => {
  it("counts events and ranks them by frequency", () => {
    const summary = summarize([
      entry({ event: "page_view" }),
      entry({ event: "page_view" }),
      entry({ event: "match_run", props: { solutions: 3 } }),
    ]);

    expect(summary.total).toBe(3);
    expect(summary.events).toEqual([
      { label: "page_view", count: 2 },
      { label: "match_run", count: 1 },
    ]);
  });

  it("breaks ties by label so equal counts do not reorder at random", () => {
    const summary = summarize([entry({ event: "zeta" }), entry({ event: "alpha" })]);
    expect(summary.events.map((e) => e.label)).toEqual(["alpha", "zeta"]);
  });

  it("ranks pages from page views only", () => {
    const summary = summarize([
      entry({ page: "/match" }),
      entry({ page: "/match" }),
      entry({ page: "/okh" }),
      // A match_run also carries a page, but counting it would double the
      // weight of a route just because something happened on it.
      entry({ event: "match_run", page: "/match", props: { solutions: 1 } }),
    ]);

    expect(summary.pages).toEqual([
      { label: "/match", count: 2 },
      { label: "/okh", count: 1 },
    ]);
  });

  it("counts match runs that returned nothing", () => {
    const summary = summarize([
      entry({ event: "match_run", props: { solutions: 0 } }),
      entry({ event: "match_run", props: { solutions: 4 } }),
      entry({ event: "match_run", props: { solutions: 0 } }),
    ]);

    expect(summary.matchRuns).toBe(3);
    expect(summary.emptyMatchRuns).toBe(2);
  });

  it("does not read a missing payload as a zero result", () => {
    // The masked read returns no props at all, and rows written before
    // match_run carried an outcome have none. Counting those as empty would
    // report failures that never happened.
    const summary = summarize([
      entry({ event: "match_run", props: null }),
      entry({ event: "match_run", props: {} }),
      entry({ event: "match_run", props: { solutions: 0 } }),
    ]);

    expect(summary.matchRuns).toBe(3);
    expect(summary.emptyMatchRuns).toBe(1);
  });

  it("names the designs behind the empty matches, ranked by how often", () => {
    // The operator-actionable list: what people came here to make that this
    // facility network cannot make.
    const summary = summarize([
      entry({ event: "match_run", props: { design: "okh-pump", solutions: 0 } }),
      entry({ event: "match_run", props: { design: "okh-pump", solutions: 0 } }),
      entry({ event: "match_run", props: { design: "okh-lathe", solutions: 0 } }),
      // A run that succeeded is not unmet demand.
      entry({ event: "match_run", props: { design: "okh-bracket", solutions: 5 } }),
    ]);

    expect(summary.unmetDemand).toEqual([
      { label: "okh-pump", count: 2 },
      { label: "okh-lathe", count: 1 },
    ]);
  });

  it("omits an empty match whose design it cannot name", () => {
    const summary = summarize([entry({ event: "match_run", props: { solutions: 0 } })]);
    expect(summary.emptyMatchRuns).toBe(1);
    expect(summary.unmetDemand).toEqual([]);
  });

  it("caps each ranking and keeps the busiest", () => {
    const many = ["a", "a", "a", "b", "b", "c", "d", "e", "f"].map((page) =>
      entry({ page: `/${page}` }),
    );
    const summary = summarize(many, 2);

    expect(summary.pages).toEqual([
      { label: "/a", count: 3 },
      { label: "/b", count: 2 },
    ]);
  });

  it("is empty rather than undefined for no activity", () => {
    expect(summarize([])).toEqual({
      total: 0,
      events: [],
      pages: [],
      matchRuns: 0,
      emptyMatchRuns: 0,
      unmetDemand: [],
    });
  });
});
