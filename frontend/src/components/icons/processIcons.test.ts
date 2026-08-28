import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { processIcon } from "./processIcons";

/**
 * The canonical ids, read from the taxonomy rather than copied here.
 *
 * A list duplicated into a test stops being a check the moment someone adds a
 * process: the copy still passes while the app renders a gap. Reading the
 * source of truth means a new process fails this until it has a glyph.
 */
function taxonomyProcessIds(): string[] {
  const yaml = readFileSync(
    join(import.meta.dirname, "../../../../src/config/taxonomy/processes.yaml"),
    "utf8",
  );
  return [...yaml.matchAll(/^ {2}([a-z0-9_]+):$/gm)].map((m) => m[1]!);
}

describe("processIcon", () => {
  it("covers every process in the taxonomy", () => {
    const ids = taxonomyProcessIds();
    expect(ids.length).toBeGreaterThan(40);
    const uncovered = ids.filter((id) => processIcon(id) === null);
    expect(
      uncovered,
      `processes with no glyph (add one to components/icons/processIcons):\n${uncovered.join("\n")}`,
    ).toEqual([]);
  });

  it("gives a family glyph to a variant it has never seen", () => {
    // A federated peer can send an id this app does not carry.
    expect(processIcon("3d_printing_mjf")).toBe(processIcon("3d_printing"));
    expect(processIcon("cnc_grinding")).toBe(processIcon("cnc_machining"));
  });

  it("prefers a process's own glyph over its family's", () => {
    expect(processIcon("3d_printing_sla")).not.toBe(processIcon("3d_printing"));
    expect(processIcon("cnc_turning")).not.toBe(processIcon("cnc_machining"));
  });

  it("tolerates the spellings a label round-trip produces", () => {
    const laser = processIcon("laser_cutting");
    expect(processIcon("Laser Cutting")).toBe(laser);
    expect(processIcon("laser-cutting")).toBe(laser);
    expect(processIcon("  LASER_CUTTING  ")).toBe(laser);
  });

  it("returns null for something that is not a process at all", () => {
    expect(processIcon("banana")).toBeNull();
    expect(processIcon("")).toBeNull();
  });
});
