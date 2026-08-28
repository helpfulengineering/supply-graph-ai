import { describe, expect, it } from "vitest";
import { CLAIM_TTL_MS, claimState, formatRemaining } from "./claimState";

const NOW = Date.parse("2026-08-12T12:00:00Z");
const hoursAgo = (h: number) => new Date(NOW - h * 3_600_000).toISOString();

describe("claimState", () => {
  it("reports a fresh claim with who holds it and how long is left", () => {
    const state = claimState(
      { claimed_by: "ana", claimed_at: hoursAgo(7) },
      NOW,
    );
    expect(state.claimed).toBe(true);
    expect(state.claimedBy).toBe("ana");
    expect(state.remainingMs).toBe(CLAIM_TTL_MS - 7 * 3_600_000);
    expect(state.label).toBe("Claimed by ana — 41h left");
  });

  it("treats a claim older than the TTL as free", () => {
    // The server checks the 48h expiry lazily, on read, so a payload can carry
    // claimed_by for a claim that has already lapsed. Trusting the field would
    // hide the claim control on a part that is actually available.
    const state = claimState(
      { claimed_by: "ana", claimed_at: hoursAgo(49) },
      NOW,
    );
    expect(state.claimed).toBe(false);
    expect(state.claimedBy).toBeNull();
    expect(state.label).toBeNull();
  });

  it("is free at exactly the TTL boundary", () => {
    expect(
      claimState({ claimed_by: "ana", claimed_at: hoursAgo(48) }, NOW).claimed,
    ).toBe(false);
  });

  it("is free when either half of the claim is absent", () => {
    expect(
      claimState({ claimed_by: "ana", claimed_at: null }, NOW).claimed,
    ).toBe(false);
    expect(
      claimState({ claimed_by: null, claimed_at: hoursAgo(1) }, NOW).claimed,
    ).toBe(false);
    expect(claimState({}, NOW).claimed).toBe(false);
  });

  it("is free when the timestamp cannot be parsed", () => {
    expect(
      claimState({ claimed_by: "ana", claimed_at: "not a date" }, NOW).claimed,
    ).toBe(false);
  });
});

describe("formatRemaining", () => {
  it("uses minutes under an hour and whole hours above it", () => {
    expect(formatRemaining(45 * 60_000)).toBe("45m");
    expect(formatRemaining(90 * 60_000)).toBe("1h");
    expect(formatRemaining(41 * 3_600_000)).toBe("41h");
  });

  it("never renders a negative remainder", () => {
    expect(formatRemaining(-5000)).toBe("0m");
  });
});
