import { describe, expect, it } from "vitest";
import { EMAIL_MAX, NAME_MAX, gateFieldErrors, gateFieldsValid } from "./gateValidation";

describe("gateFieldErrors", () => {
  it("accepts an ordinary name and address", () => {
    expect(gateFieldErrors("Ada Lovelace", "ada@example.org")).toEqual({});
    expect(gateFieldsValid(gateFieldErrors("Ada Lovelace", "ada@example.org"))).toBe(true);
  });

  it("treats whitespace-only input as empty, as the RPC's trim does", () => {
    const errors = gateFieldErrors("   ", "  ");
    expect(errors.name).toMatch(/name/i);
    expect(errors.email).toMatch(/email/i);
  });

  it("rejects the addresses the SQL regex rejects", () => {
    for (const bad of ["ada", "ada@example", "ada@ex ample.org", "a@b@c.org", "@example.org"]) {
      expect(gateFieldErrors("Ada", bad).email, bad).toBeTruthy();
    }
  });

  it("enforces the same length caps as the schema", () => {
    expect(gateFieldErrors("a".repeat(NAME_MAX), "ada@example.org").name).toBeUndefined();
    expect(gateFieldErrors("a".repeat(NAME_MAX + 1), "ada@example.org").name).toBeTruthy();

    const long = `${"a".repeat(EMAIL_MAX - "@example.org".length + 1)}@example.org`;
    expect(long.length).toBeGreaterThan(EMAIL_MAX);
    expect(gateFieldErrors("Ada", long).email).toBeTruthy();
  });

  it("does not count surrounding whitespace toward the caps", () => {
    expect(gateFieldErrors(`  ${"a".repeat(NAME_MAX)}  `, " ada@example.org ")).toEqual({});
  });
});
