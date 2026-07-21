import { describe, expect, it } from "vitest";
import { certifyRelease, listAttestations, listReputation } from "./identity";
import { bundleHashFromPin } from "../package";
import {
  attestationsFixture,
  identityFixture,
  pinRecordFixture,
} from "../../test/fixtures";

describe("identity F4 wrappers", () => {
  it("lists attestations by content hash", async () => {
    const items = await listAttestations({
      content_hash: attestationsFixture[0]!.content_hash!,
    });
    expect(items.some((a) => a.type === "certified")).toBe(true);
  });

  it("certifies a release", async () => {
    const a = await certifyRelease({
      subject_did: identityFixture.did,
      bundle_hash: "sha256:bundlehash0000000000000000000000000001",
      version: "1.0.0",
      manifest_content_hash: pinRecordFixture.manifest_content_hash,
    });
    expect(a.type).toBe("certified");
  });

  it("lists reputation for a subject", async () => {
    const items = await listReputation(identityFixture.did);
    expect(items.map((a) => a.type)).toEqual(
      expect.arrayContaining(["certified", "domain_bound", "vouch"]),
    );
  });
});

describe("bundleHashFromPin", () => {
  it("matches single-leaf merkle (manifest only)", async () => {
    const hash = await bundleHashFromPin(pinRecordFixture);
    expect(hash).toBe(`sha256:${pinRecordFixture.manifest_content_hash}`);
  });
});
