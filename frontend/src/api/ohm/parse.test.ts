import { describe, expect, it } from "vitest";
import { z } from "zod";
import { ApiError } from "./client";
import { parsePayload } from "./parse";

const schema = z.looseObject({
  root_components: z.array(z.looseObject({ component_name: z.string() })),
});

describe("parsePayload", () => {
  it("returns the payload when it matches", () => {
    const payload = { root_components: [{ component_name: "Frame" }] };
    expect(parsePayload("/x", schema, payload)).toEqual(payload);
  });

  it("names the endpoint and the field when the shape drifts", () => {
    // The #369 payload: objects where the client expected strings. Before, this
    // surfaced as a minified React error deep in a render.
    expect(() =>
      parsePayload("/api/hierarchy", schema, {
        root_components: ["frame"],
      }),
    ).toThrow(/\/api\/hierarchy.*root_components\.0/);
  });

  it("throws ApiError naming the missing key, so callers handle it like any other API failure", () => {
    expect(() => parsePayload("/api/hierarchy", schema, {})).toThrow(ApiError);
    expect(() => parsePayload("/api/hierarchy", schema, {})).toThrow(
      /root_components/,
    );
  });

  it("keeps fields the schema does not describe", () => {
    // Load-bearing. A stripping parse would silently drop server data at the
    // client — the same failure mode that makes response_model dangerous to
    // hand-write, rebuilt one layer down.
    const payload = {
      root_components: [{ component_name: "Frame", tree_id: "t-1" }],
      component_details: { frame: { anything: true } },
    };
    expect(parsePayload("/x", schema, payload)).toEqual(payload);
  });
});
