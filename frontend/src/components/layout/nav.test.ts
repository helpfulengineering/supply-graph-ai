import { describe, it, expect } from "vitest";
import { ALL_GROUPS, NAV_GROUPS, navEntryFor, navEntryPath } from "./nav";

/**
 * The sitemap is load-bearing in three places now — the drawer, the Help page,
 * and every page's hero — so the resolution rule it all rests on is asserted
 * rather than assumed. The property that matters: the glyph you clicked is the
 * glyph you land under.
 */

describe("navEntryFor", () => {
  it("resolves a list route to its own entry", () => {
    expect(navEntryFor("/okh")?.entry.name).toBe("Designs");
    expect(navEntryFor("/facilities")?.entry.name).toBe("Facilities");
  });

  it("gives a detail route the icon of the list it came from", () => {
    // The whole point of prefix matching: /okh/okh-0001 has no sitemap row of
    // its own, and a design detail page belongs to the design catalog.
    expect(navEntryFor("/okh/okh-0001")?.entry.icon).toBe(
      navEntryFor("/okh")?.entry.icon,
    );
    expect(navEntryFor("/okh/okh-0001/files/readme.md")?.entry.name).toBe(
      "Designs",
    );
    expect(navEntryFor("/facilities/okw-1/edit")?.entry.name).toBe("Facilities");
  });

  it("prefers the longer match when a sub-route has its own entry", () => {
    // Shortest-first would hand /okh/new and /okh/generate to the catalog,
    // which is the bug this ordering exists to prevent.
    expect(navEntryFor("/okh/new")?.entry.name).toBe("New design");
    expect(navEntryFor("/okh/generate")?.entry.name).toBe("Generate");
    expect(navEntryFor("/facilities/new")?.entry.name).toBe("New facility");
  });

  it("keeps Settings resolved across its subtabs", () => {
    for (const path of [
      "/settings",
      "/settings/session",
      "/settings/bindings",
      "/settings/directory",
    ]) {
      expect(navEntryFor(path)?.entry.name, path).toBe("Settings");
    }
  });

  it("does not let the dashboard swallow every route", () => {
    expect(navEntryFor("/")?.entry.name).toBe("Dashboard");
    expect(navEntryFor("/match")?.entry.name).toBe("Match");
  });

  it("resolves routes that are deliberately absent from the menu", () => {
    // A supply tree is a match result rather than a browsable collection, so
    // it is not in the drawer — but it is a page, and it needs a hero.
    expect(navEntryFor("/visualization/sol-1")?.entry.name).toBe("Supply Tree");
    expect(
      NAV_GROUPS.flatMap((g) => g.entries).some(
        (e) => e.href === "/visualization",
      ),
    ).toBe(false);
  });

  it("returns nothing outside the app", () => {
    expect(navEntryFor("/nope")).toBeUndefined();
  });

  it("never resolves to an external link", () => {
    // /docs/ is a static mkdocs site on the same origin. It has a menu row but
    // no hero of ours to put an icon on.
    expect(navEntryFor("/docs/")).toBeUndefined();
  });
});

describe("the sitemap is well formed", () => {
  it("claims each path exactly once", () => {
    const paths = ALL_GROUPS.flatMap((g) => g.entries).map(navEntryPath);
    expect(paths).toEqual([...new Set(paths)]);
  });

  it("gives every entry an icon and a role line", () => {
    for (const group of ALL_GROUPS) {
      for (const entry of group.entries) {
        expect(entry.icon, `${entry.href} icon`).toBeTruthy();
        expect(entry.desc, `${entry.href} desc`).not.toBe("");
      }
    }
  });

  it("gives every group a token accent rather than a literal colour", () => {
    for (const group of ALL_GROUPS) {
      expect(group.accent, group.label).toMatch(/^text-chart-[1-5]$/);
    }
  });
});
