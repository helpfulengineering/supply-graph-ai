import { describe, expect, it } from "vitest";
import {
  bindOAuth,
  listBindings,
  listDirectory,
  publishDirectoryEntry,
  startDomainBinding,
  verifyDomainBinding,
} from "./identity";
import {
  bindingsFixture,
  directoryFixture,
  domainBindStartFixture,
  identityFixture,
} from "../../test/fixtures";

describe("identity F5 wrappers", () => {
  it("starts and verifies a domain binding", async () => {
    const started = await startDomainBinding(identityFixture.did, "example.org");
    expect(started.well_known_url).toBe(domainBindStartFixture.well_known_url);
    expect(started.well_known_document.challenge).toBe("test-challenge-token");

    const verified = await verifyDomainBinding(identityFixture.did, "example.org");
    expect(verified.verified).toBe(true);
  });

  it("records an OAuth binding and lists bindings", async () => {
    const bound = await bindOAuth({
      subject_did: identityFixture.did,
      provider: "github",
      external_subject: "octocat",
    });
    expect(bound.external_id).toContain("oauth:github:");
    const list = await listBindings();
    expect(list).toHaveLength(bindingsFixture.length);
  });

  it("lists and publishes directory entries", async () => {
    const entries = await listDirectory();
    expect(entries[0]?.did).toBe(directoryFixture[0]!.did);
    const published = await publishDirectoryEntry({
      did: identityFixture.did,
      display_name: "Local admin",
      base_url: "https://ohm.example.org",
      domain: "example.org",
    });
    expect(published.display_name).toBe("Local admin");
  });
});
