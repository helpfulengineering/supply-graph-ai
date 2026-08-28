import { describe, expect, it } from "vitest";
import {
  EMPTY_SALVAGE_QUERY,
  isSalvageQueryRunnable,
  salvageQueryError,
  salvageQueryFromParams,
  salvageQueryToParams,
  toSalvageRequest,
} from "./salvageQuery";

const params = (search: string) => new URLSearchParams(search);

describe("salvageQueryFromParams", () => {
  it("reads every field the form holds", () => {
    const query = salvageQueryFromParams(
      params(
        "component=pump&part=P-1&design=okh-1&conditions=intact,damaged&claimed=1",
      ),
    );
    expect(query).toEqual({
      componentName: "pump",
      partNumber: "P-1",
      manifestId: "okh-1",
      conditions: ["intact", "damaged"],
      includeClaimed: true,
    });
  });

  it("drops conditions the API does not accept", () => {
    // A hand-edited URL should narrow the search, not 422 it.
    const query = salvageQueryFromParams(params("conditions=intact,melted"));
    expect(query.conditions).toEqual(["intact"]);
  });

  it("reads an empty search as the empty query", () => {
    expect(salvageQueryFromParams(params(""))).toEqual(EMPTY_SALVAGE_QUERY);
  });
});

describe("salvageQueryToParams", () => {
  it("writes only what was set, so a plain search has a plain URL", () => {
    const query = { ...EMPTY_SALVAGE_QUERY, componentName: "pump" };
    expect(salvageQueryToParams(query).toString()).toBe("component=pump");
  });

  it("omits conditions when every condition is selected", () => {
    const query = {
      ...EMPTY_SALVAGE_QUERY,
      componentName: "pump",
      conditions: ["intact", "damaged", "missing", "unknown"] as const,
    };
    expect(
      salvageQueryToParams({ ...query, conditions: [...query.conditions] }).has(
        "conditions",
      ),
    ).toBe(false);
  });

  it("round-trips a filled query", () => {
    const query = {
      componentName: "pump",
      partNumber: "P-1",
      manifestId: "okh-1",
      conditions: ["damaged" as const],
      includeClaimed: true,
    };
    expect(salvageQueryFromParams(salvageQueryToParams(query))).toEqual(query);
  });
});

describe("salvageQueryError", () => {
  it("names the server's one rule before the request is made", () => {
    // The backend 422s without a name or a part number, and the control that
    // would explain that is the one you did not fill in.
    expect(salvageQueryError(EMPTY_SALVAGE_QUERY)).toMatch(
      /component name or a part/,
    );
    expect(isSalvageQueryRunnable(EMPTY_SALVAGE_QUERY)).toBe(false);
  });

  it("accepts either field alone", () => {
    expect(
      salvageQueryError({ ...EMPTY_SALVAGE_QUERY, componentName: "pump" }),
    ).toBeNull();
    expect(
      salvageQueryError({ ...EMPTY_SALVAGE_QUERY, partNumber: "P-1" }),
    ).toBeNull();
  });

  it("does not accept whitespace as a value", () => {
    expect(
      salvageQueryError({ ...EMPTY_SALVAGE_QUERY, componentName: "   " }),
    ).not.toBeNull();
  });
});

describe("toSalvageRequest", () => {
  it("inverts includeClaimed into the server's exclude_claimed", () => {
    const request = toSalvageRequest({
      ...EMPTY_SALVAGE_QUERY,
      componentName: "pump",
      includeClaimed: true,
    });
    expect(request.exclude_claimed).toBe(false);
  });

  it("sends nulls rather than empty strings for unset filters", () => {
    const request = toSalvageRequest({
      ...EMPTY_SALVAGE_QUERY,
      componentName: "pump",
    });
    expect(request).toEqual({
      component_name: "pump",
      part_number: null,
      manifest_id: null,
      conditions: null,
      exclude_claimed: true,
    });
  });
});
