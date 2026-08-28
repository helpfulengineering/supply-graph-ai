import { describe, expect, it } from "vitest";
import { NAV_GROUPS, navGroupsForDomain } from "./nav";

/**
 * Replaces the coverage `navItemsForDomain` carried before the Next migration.
 * The assertions are the same promises — cooking renames the two browse rows
 * and drops manufacturing authoring — against the sitemap that now backs them.
 */
describe("navGroupsForDomain", () => {
  const names = (domain: "manufacturing" | "cooking") =>
    navGroupsForDomain(domain).flatMap((g) => g.entries.map((e) => e.name));

  it("leaves the manufacturing sitemap untouched", () => {
    expect(navGroupsForDomain("manufacturing")).toBe(NAV_GROUPS);
    expect(names("manufacturing")).toEqual(
      expect.arrayContaining(["Designs", "Facilities", "Packages", "Match"]),
    );
  });

  it("renames the two browse rows for cooking", () => {
    expect(names("cooking")).toEqual(
      expect.arrayContaining(["Recipes", "Kitchens"]),
    );
    expect(names("cooking")).not.toContain("Designs");
    expect(names("cooking")).not.toContain("Facilities");
  });

  it("drops manufacturing authoring and browse rows for cooking", () => {
    for (const gone of ["Packages", "Match", "Generate", "New design", "RFQ"]) {
      expect(names("cooking")).not.toContain(gone);
    }
  });

  it("keeps the cooking rows pointing at the same routes", () => {
    const byName = Object.fromEntries(
      navGroupsForDomain("cooking").flatMap((g) =>
        g.entries.map((e) => [e.name, e.href]),
      ),
    );
    expect(byName["Recipes"]).toBe("/okh");
    expect(byName["Kitchens"]).toBe("/facilities");
  });

  it("keeps Reference, which is about the app rather than the domain", () => {
    expect(names("cooking")).toContain("Help");
  });
});
