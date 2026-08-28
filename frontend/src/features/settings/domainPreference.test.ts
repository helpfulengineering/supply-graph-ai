import { describe, expect, it } from "vitest";
import {
  DEFAULT_DOMAIN,
  parseDomain,
} from "./domainPreference";

describe("parseDomain", () => {
  it("defaults to manufacturing for null/empty/invalid", () => {
    expect(DEFAULT_DOMAIN).toBe("manufacturing");
    expect(parseDomain(null)).toBe("manufacturing");
    expect(parseDomain("")).toBe("manufacturing");
    expect(parseDomain("unknown")).toBe("manufacturing");
  });

  it("accepts manufacturing and cooking", () => {
    expect(parseDomain("manufacturing")).toBe("manufacturing");
    expect(parseDomain("cooking")).toBe("cooking");
  });
});

