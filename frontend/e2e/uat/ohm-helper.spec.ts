import { test, expect } from "@playwright/test";
import { OhmError, ohm, ohmAsBootstrap } from "./ohm";

/**
 * The helper every later part leans on, checked before any of them run.
 *
 * The identity CLI exits 0 and prints nothing when the node answers 401. A
 * helper that returned that empty result would let a part "pass" on a
 * credential the node never accepted, so empty output has to be an error.
 * These are the only two things the helper promises.
 */
test.describe("@membership ohm helper", () => {
  test("a refused key throws instead of returning nothing", async () => {
    await expect(
      ohm("ohm_this_key_was_never_issued", ["identity", "whoami"]),
    ).rejects.toBeInstanceOf(OhmError);
  });

  test("the bootstrap key is accepted", async () => {
    const who = await ohmAsBootstrap(["identity", "whoami"]);
    expect(who.permissions).toContain("admin");
  });
});
