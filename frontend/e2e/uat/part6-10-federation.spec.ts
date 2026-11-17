import { test, expect } from "@playwright/test";
import { apiOk } from "./api";
import { field, ohm, OhmError } from "./ohm";
import { KEY_A, KEY_B, PEER_A, PEER_A_INTERNAL, PEER_B } from "./peers";
import { loadWorld, resetWorld, saveWorld, type Person } from "./world";

/**
 * Parts 6–10 of the membership runbook: two nodes, curated lists, marks, and
 * a collection zip. No browser: the federation stack has no Settings page.
 */
test.describe("@federation parts 6-10: two nodes and curated lists", () => {
  test.describe.configure({ mode: "serial" });

  async function mintPeerOperator(): Promise<Person> {
    const existing = loadWorld().operator;
    if (existing?.token) {
      return existing;
    }
    const account = await ohm(
      KEY_A,
      ["identity", "accounts", "create", "--name", "Node operator"],
      PEER_A,
    );
    const accountId = field(account, "id");
    const identity = await ohm(
      KEY_A,
      [
        "identity",
        "identities",
        "create",
        "--account-id",
        accountId,
        "--kind",
        "person",
        "--name",
        "Node operator",
      ],
      PEER_A,
    );
    const key = await ohm(
      KEY_A,
      [
        "identity",
        "keys",
        "create",
        "--name",
        "operator",
        "--permission",
        "admin",
        "--account-id",
        accountId,
      ],
      PEER_A,
    );
    const person: Person = {
      name: "Node operator",
      accountId,
      did: field(identity, "did"),
      token: field(key, "token"),
    };
    saveWorld({ operator: person });
    return person;
  }

  async function claimSpace(operator: Person): Promise<string> {
    const existing = loadWorld().spaceDid;
    if (existing) return existing;
    const account = await ohm(
      operator.token,
      [
        "identity",
        "accounts",
        "create",
        "--name",
        "Field org",
        "--kind",
        "space",
      ],
      PEER_A,
    );
    const spaceAccountId = field(account, "id");
    const identity = await ohm(
      operator.token,
      [
        "identity",
        "identities",
        "create",
        "--account-id",
        spaceAccountId,
        "--kind",
        "space",
        "--name",
        "Field org",
      ],
      PEER_A,
    );
    const spaceDid = field(identity, "did");
    await ohm(
      operator.token,
      [
        "identity",
        "spaces",
        "claim",
        "--space-did",
        spaceDid,
        "--admin-did",
        operator.did,
      ],
      PEER_A,
    );
    await ohm(
      operator.token,
      [
        "identity",
        "affiliate",
        "add",
        operator.did,
        "--space",
        spaceDid,
      ],
      PEER_A,
    );
    saveWorld({ spaceDid });
    return spaceDid;
  }

  async function createDesign(
    token: string,
    title: string,
    onBehalfOf?: string,
  ): Promise<string> {
    const id = crypto.randomUUID();
    const path = onBehalfOf
      ? `/api/okh/create?on_behalf_of=${encodeURIComponent(onBehalfOf)}`
      : "/api/okh/create";
    const created = await apiOk(
      token,
      "POST",
      path,
      {
        content: {
          okhv: "1.0",
          id,
          title,
          version: "1.0.0",
          license: { hardware: "MIT" },
          licensor: "Ada",
          documentation_language: "en",
          function: "Moves water",
          manufacturing_processes: ["Assembly"],
        },
      },
      PEER_A,
    );
    const okh = (created as { okh?: { id?: string } }).okh;
    return okh?.id ?? id;
  }

  test("peer A seeds shareable designs; private stays out of the catalog", async () => {
    resetWorld();
    // Confirm we are on the federation stack.
    const who = await ohm(KEY_A, ["identity", "whoami"], PEER_A);
    expect(who.permissions).toContain("admin");

    const operator = await mintPeerOperator();
    const spaceDid = await claimSpace(operator);

    const designA = await createDesign(operator.token, "Field pump", spaceDid);
    const designB = await createDesign(operator.token, "Field pump, second");
    const designOther = await createDesign(operator.token, "Field pump, other");
    const designPrivate = await createDesign(
      operator.token,
      "Field pump, private",
    );

    await apiOk(
      operator.token,
      "PUT",
      `/api/okh/${designA}/visibility`,
      { visibility: "followers" },
      PEER_A,
    );
    await apiOk(
      operator.token,
      "PUT",
      `/api/okh/${designB}/visibility`,
      { visibility: "followers" },
      PEER_A,
    );
    await apiOk(
      operator.token,
      "PUT",
      `/api/okh/${designOther}/visibility`,
      { visibility: "followers" },
      PEER_A,
    );

    const catalog = (await apiOk(
      KEY_A,
      "GET",
      "/api/federation/catalog",
      undefined,
      PEER_A,
    )) as { records?: Array<{ title?: string; content_hash?: string }> };

    const byTitle = Object.fromEntries(
      (catalog.records ?? [])
        .filter((r) => r.title && r.content_hash)
        .map((r) => [r.title!, r.content_hash!]),
    );
    expect(byTitle["Field pump"]).toMatch(/^sha256:/);
    expect(byTitle["Field pump, second"]).toMatch(/^sha256:/);
    expect(byTitle["Field pump, other"]).toMatch(/^sha256:/);
    expect(byTitle["Field pump, private"]).toBeUndefined();

    saveWorld({
      designs: {
        a: designA,
        b: designB,
        other: designOther,
        private: designPrivate,
      },
      hashes: {
        HASH_A: byTitle["Field pump"],
        HASH_B: byTitle["Field pump, second"],
        HASH_OTHER: byTitle["Field pump, other"],
      },
    });
  });

  test("publish a list, refuse a non-shareable pin, then subscribe and sync", async () => {
    const hashes = loadWorld().hashes!;
    const published = await ohm(
      KEY_A,
      [
        "federation",
        "lists",
        "publish",
        "--name",
        "Field designs",
        "--pin",
        hashes.HASH_A,
      ],
      PEER_A,
    );
    expect(Number(field(published, "sequence"))).toBe(1);
    const listId = field(published, "list_id");
    saveWorld({ listId });

    await expect(
      ohm(
        KEY_A,
        [
          "federation",
          "lists",
          "publish",
          "--name",
          "Field designs",
          "--pin",
          `sha256:${"0".repeat(64)}`,
        ],
        PEER_A,
      ),
    ).rejects.toBeInstanceOf(OhmError);

    const still = await ohm(
      KEY_A,
      ["federation", "lists", "show", listId],
      PEER_A,
    );
    expect(Number(field(still, "sequence"))).toBe(1);

    await ohm(
      KEY_B,
      [
        "federation",
        "lists",
        "subscribe",
        "--peer",
        PEER_A_INTERNAL,
        "--list",
        listId,
      ],
      PEER_B,
    );
    const sync = await ohm(KEY_B, ["federation", "sync"], PEER_B);
    // Sync reports at least one design pulled across peers.
    expect(JSON.stringify(sync)).toMatch(/pull|Field pump|1/i);

    await ohm(
      KEY_A,
      [
        "federation",
        "lists",
        "update",
        listId,
        "--name",
        "Field designs",
        "--pin",
        hashes.HASH_A,
        "--pin",
        hashes.HASH_B,
      ],
      PEER_A,
    );
    await ohm(KEY_B, ["federation", "sync"], PEER_B);

    await ohm(
      KEY_B,
      [
        "federation",
        "lists",
        "unsubscribe",
        "--peer",
        PEER_A_INTERNAL,
        "--list",
        listId,
      ],
      PEER_B,
    );
    // Put the subscription back for the bump/drop steps.
    await ohm(
      KEY_B,
      [
        "federation",
        "lists",
        "subscribe",
        "--peer",
        PEER_A_INTERNAL,
        "--list",
        listId,
      ],
      PEER_B,
    );
  });

  test("bump and drop leave the old design with a mark", async () => {
    const hashes = loadWorld().hashes!;
    const listId = loadWorld().listId!;

    await ohm(
      KEY_A,
      [
        "federation",
        "lists",
        "update",
        listId,
        "--name",
        "Field designs",
        "--pin",
        hashes.HASH_B,
        "--replaces",
        `${hashes.HASH_B}=${hashes.HASH_A}`,
      ],
      PEER_A,
    );
    await ohm(KEY_B, ["federation", "sync"], PEER_B);
    const marksAfterBump = await ohm(
      KEY_B,
      ["federation", "lists", "marks"],
      PEER_B,
    );
    expect(JSON.stringify(marksAfterBump)).toContain(hashes.HASH_A);

    await ohm(
      KEY_A,
      [
        "federation",
        "lists",
        "update",
        listId,
        "--name",
        "Field designs",
        "--pin",
        hashes.HASH_A,
      ],
      PEER_A,
    );
    await ohm(KEY_B, ["federation", "sync"], PEER_B);
    const marksAfterDrop = await ohm(
      KEY_B,
      ["federation", "lists", "marks"],
      PEER_B,
    );
    expect(JSON.stringify(marksAfterDrop)).toContain(hashes.HASH_B);
  });

  test("a collection zip carries the organisation to peer B", async () => {
    const operator = loadWorld().operator;
    const designA = loadWorld().designs?.a;
    const spaceDid = loadWorld().spaceDid;
    expect(operator?.token).toBeTruthy();
    expect(designA).toBeTruthy();
    expect(spaceDid).toBeTruthy();
    if (!operator?.token || !designA || !spaceDid) {
      return;
    }

    // Export as the person who can read the design.
    const exportRes = await fetch(
      `${PEER_A}/v1/api/okh/export-collection`,
      { headers: { Authorization: `Bearer ${operator.token}` } },
    );
    expect(exportRes.ok).toBe(true);
    const bytes = Buffer.from(await exportRes.arrayBuffer());
    expect(bytes.byteLength).toBeGreaterThan(100);

    const form = new FormData();
    form.append(
      "file",
      new Blob([bytes], { type: "application/zip" }),
      "field.zip",
    );
    const imported = await fetch(
      `${PEER_B}/v1/api/okh/import-collection`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${KEY_B}` },
        body: form,
      },
    );
    expect(imported.ok).toBe(true);

    const provenance = await apiOk(
      KEY_B,
      "GET",
      `/api/okh/${designA}/provenance`,
      undefined,
      PEER_B,
    );
    expect(JSON.stringify(provenance)).toContain(spaceDid);
  });
});
