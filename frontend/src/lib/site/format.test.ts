import { describe, expect, it } from "vitest";
import { age, instant, since } from "./format";

const NOW = Date.parse("2026-08-11T12:00:00.000Z");

function ago(ms: number): string {
  return new Date(NOW - ms).toISOString();
}

describe("age", () => {
  it("collapses the last minute to 'just now'", () => {
    expect(age(ago(0), NOW)).toBe("just now");
    expect(age(ago(59_000), NOW)).toBe("just now");
  });

  it("steps up through minutes, hours, and days", () => {
    expect(age(ago(60_000), NOW)).toBe("1m");
    expect(age(ago(6 * 60_000), NOW)).toBe("6m");
    expect(age(ago(60 * 60_000), NOW)).toBe("1h");
    expect(age(ago(3 * 60 * 60_000), NOW)).toBe("3h");
    expect(age(ago(24 * 60 * 60_000), NOW)).toBe("1d");
    expect(age(ago(12 * 24 * 60 * 60_000), NOW)).toBe("12d");
  });

  it("reads a timestamp slightly ahead of this clock as 'just now'", () => {
    // Row written by a server whose clock leads this one — "in 2 seconds" is
    // never the useful reading of a row that was just inserted.
    expect(age(new Date(NOW + 2_000).toISOString(), NOW)).toBe("just now");
  });

  it("renders a dash for a missing or unparseable timestamp", () => {
    expect(age(null, NOW)).toBe("—");
    expect(age("", NOW)).toBe("—");
    expect(age("not a date", NOW)).toBe("—");
  });
});

describe("since", () => {
  it("adds the preposition where it belongs", () => {
    expect(since(ago(6 * 60_000), NOW)).toBe("6m ago");
    expect(since(ago(3 * 24 * 60 * 60_000), NOW)).toBe("3d ago");
  });

  it("leaves the two cases that do not take one", () => {
    // "last seen just now ago" and "last seen — ago" are what a naive join
    // produces; both read as a bug to anyone looking at the panel.
    expect(since(ago(0), NOW)).toBe("just now");
    expect(since(null, NOW)).toBe("—");
  });
});

describe("instant", () => {
  it("is empty when there is nothing to show, so the title is dropped", () => {
    expect(instant(null)).toBe("");
    expect(instant("not a date")).toBe("");
  });

  it("renders a parseable timestamp", () => {
    expect(instant("2026-08-11T12:00:00.000Z")).not.toBe("");
  });
});
