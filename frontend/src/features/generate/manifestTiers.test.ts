import { describe, expect, it } from "vitest";
import {
  getPath,
  isEmptyValue,
  missingRequired,
  REQUIRED_PATHS,
  setPath,
  tier3Fields,
} from "./manifestTiers";

describe("getPath / setPath", () => {
  it("reads a nested path", () => {
    expect(getPath({ license: { hardware: "CC-BY-4.0" } }, "license.hardware")).toBe(
      "CC-BY-4.0",
    );
  });

  it("returns undefined for a missing path rather than throwing", () => {
    expect(getPath({}, "a.b.c")).toBeUndefined();
    expect(getPath({ a: "scalar" }, "a.b")).toBeUndefined();
  });

  it("sets a nested path without mutating the original", () => {
    const original = { license: { hardware: "old" }, title: "t" };
    const next = setPath(original, "license.hardware", "new");
    expect(next.license).toEqual({ hardware: "new" });
    expect(original.license).toEqual({ hardware: "old" });
    expect(next.title).toBe("t");
  });

  it("creates intermediate objects when they are absent", () => {
    expect(setPath({}, "licensor.name", "Ada")).toEqual({ licensor: { name: "Ada" } });
  });

  it("replaces a scalar standing where an object is needed", () => {
    expect(setPath({ licensor: "someone" }, "licensor.name", "Ada")).toEqual({
      licensor: { name: "Ada" },
    });
  });
});

describe("isEmptyValue", () => {
  it("treats blank strings, empty lists and empty objects as empty", () => {
    for (const v of [null, undefined, "", "   ", [], {}]) {
      expect(isEmptyValue(v)).toBe(true);
    }
  });

  it("treats real values as present, including false and zero", () => {
    for (const v of ["x", ["a"], { a: 1 }, 0, false]) {
      expect(isEmptyValue(v)).toBe(false);
    }
  });
});

describe("missingRequired", () => {
  it("lists every unfilled required path", () => {
    expect(missingRequired({})).toEqual(REQUIRED_PATHS);
  });

  it("is empty for a complete manifest", () => {
    const complete = {
      title: "Thing",
      version: "1.0.0",
      function: "Does a thing",
      documentation_language: "en",
      licensor: { name: "Ada" },
      license: { hardware: "CC-BY-4.0" },
    };
    expect(missingRequired(complete)).toEqual([]);
  });

  it("catches a required nested leaf that is blank", () => {
    const m = {
      title: "Thing",
      version: "1.0.0",
      function: "Does a thing",
      documentation_language: "en",
      licensor: { name: "  " },
      license: { hardware: "CC-BY-4.0" },
    };
    expect(missingRequired(m)).toEqual(["licensor.name"]);
  });
});

describe("tier3Fields", () => {
  it("returns unclassified keys only", () => {
    const paths = tier3Fields({
      title: "t",
      manufacturing_processes: ["3D Printing"],
      license: { hardware: "x" },
      licensor: { name: "y" },
      something_odd: "v",
    }).map((f) => f.path);
    expect(paths).toEqual(["something_odd"]);
  });

  it("never hides a generated field", () => {
    const fields = tier3Fields({ extra_one: 1, extra_two: 2 });
    expect(fields.map((f) => f.path)).toEqual(["extra_one", "extra_two"]);
  });

  it("classifies kinds so nested data is not offered a scalar input", () => {
    const byPath = Object.fromEntries(
      tier3Fields({
        a_scalar: "x",
        a_list: ["x", "y"],
        an_object: { k: 1 },
        list_of_objects: [{ k: 1 }],
      }).map((f) => [f.path, f.kind]),
    );
    expect(byPath).toEqual({
      a_scalar: "scalar",
      a_list: "list",
      an_object: "nested",
      list_of_objects: "nested",
    });
  });
});
