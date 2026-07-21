import { describe, expect, it } from "vitest";
import {
  claimSpace,
  getIdentity,
  listGrants,
  listSpaceClaims,
  mintIdentity,
} from "./identity";
import { identityFixture, grantsFixture, spaceClaimsFixture } from "../../test/fixtures";

describe("identity F3 wrappers", () => {
  it("mints an identity", async () => {
    const id = await mintIdentity({
      account_id: "00000000-0000-0000-0000-000000000001",
      kind: "person",
      display_name: "Local admin",
    });
    expect(id.did).toBe(identityFixture.did);
    expect(id.custodial).toBe(true);
  });

  it("loads an identity by DID", async () => {
    const id = await getIdentity(identityFixture.did);
    expect(id.kind).toBe("person");
  });

  it("lists grants for a subject", async () => {
    const grants = await listGrants(identityFixture.did);
    expect(grants).toHaveLength(grantsFixture.length);
    expect(grants[0]?.scope.kind).toBe("space");
  });

  it("lists and claims spaces", async () => {
    const claims = await listSpaceClaims();
    expect(claims[0]?.space_did).toBe(spaceClaimsFixture[0].space_did);
    const claimed = await claimSpace(
      spaceClaimsFixture[0].space_did,
      spaceClaimsFixture[0].admin_did,
    );
    expect(claimed.admin_did).toBe(spaceClaimsFixture[0].admin_did);
  });
});
