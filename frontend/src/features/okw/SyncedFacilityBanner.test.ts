import { describe, expect, it } from "vitest";
import {
  isSyncedFacilityProvenance,
} from "./SyncedFacilityBanner";

describe("isSyncedFacilityProvenance", () => {
  it("is true when a credit has role synced_from", () => {
    expect(
      isSyncedFacilityProvenance({
        authored_by: [
          { subject_did: "did:key:zPeer", role: "synced_from" },
        ],
        published_by: "did:key:zPeer",
        on_behalf_of: null,
        signed_by: null,
        signature: "",
      }),
    ).toBe(true);
  });

  it("is false for local authorship", () => {
    expect(
      isSyncedFacilityProvenance({
        authored_by: [{ subject_did: "did:key:zMe", role: "author" }],
        published_by: "did:key:zMe",
        on_behalf_of: null,
        signed_by: null,
        signature: "",
      }),
    ).toBe(false);
    expect(isSyncedFacilityProvenance(null)).toBe(false);
  });
});
