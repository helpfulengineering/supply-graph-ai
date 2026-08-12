import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { PROCESS_FAMILY_INK, processFamily } from "./processFamily";

/**
 * The canonical ids, read from the taxonomy rather than copied here — same
 * reasoning as the glyph coverage test: a copied list still passes on the day
 * someone adds a process and the app renders a chip with no colour.
 */
function taxonomyProcessIds(): string[] {
  const yaml = readFileSync(
    join(import.meta.dirname, "../../../../src/config/taxonomy/processes.yaml"),
    "utf8",
  );
  return [...yaml.matchAll(/^ {2}([a-z0-9_]+):$/gm)].map((m) => m[1]!);
}

describe("processFamily", () => {
  it("covers every process in the taxonomy", () => {
    const ids = taxonomyProcessIds();
    expect(ids.length).toBeGreaterThan(40);
    const uncovered = ids.filter((id) => processFamily(id) === null);
    expect(
      uncovered,
      `processes with no family (add one to components/ui/processFamily):\n${uncovered.join("\n")}`,
    ).toEqual([]);
  });

  it("gives every family an ink", () => {
    const families = new Set(
      taxonomyProcessIds().map((id) => processFamily(id)!),
    );
    for (const family of families) {
      expect(PROCESS_FAMILY_INK[family]).toBeTruthy();
    }
  });

  it("groups the processes a reader would group", () => {
    expect(processFamily("laser_cutting")).toBe(processFamily("cnc_machining"));
    expect(processFamily("pcb_assembly")).toBe(processFamily("welding"));
    expect(processFamily("annealing")).toBe(processFamily("polishing"));
    expect(processFamily("3d_printing")).not.toBe(processFamily("casting"));
  });

  it("places a variant it has never seen with its family", () => {
    // A federated peer can send an id this app does not carry.
    expect(processFamily("3d_printing_mjf")).toBe("additive");
    expect(processFamily("cnc_grinding")).toBe("subtractive");
    expect(processFamily("spot_welding")).toBe("joining");
  });

  it("tolerates the spellings a label round-trip produces", () => {
    expect(processFamily("Laser Cutting")).toBe("subtractive");
    expect(processFamily("laser-cutting")).toBe("subtractive");
    expect(processFamily("  LASER_CUTTING  ")).toBe("subtractive");
  });

  it("returns null for something that is not a process at all", () => {
    expect(processFamily("banana")).toBeNull();
    expect(processFamily("")).toBeNull();
  });
});
