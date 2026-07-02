import { describe, expect, it } from "vitest";
import { healthFixture } from "./fixtures";

// Unit-layer smoke: proves vitest runs and the MSW mock API answers fetches
// with shared fixtures (the mechanism every unit/component test relies on).
describe("harness: unit + MSW", () => {
  it("runs a plain assertion", () => {
    expect(1 + 1).toBe(2);
  });

  it("intercepts fetch with the shared health fixture", async () => {
    const res = await fetch("http://localhost:8001/health");
    const body = await res.json();
    expect(body).toEqual(healthFixture);
  });
});
