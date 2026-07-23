import { describe, expect, it } from "vitest";
import {
  fetchFederationStatus,
  followFederationPeer,
  listFederationPeers,
  runFederationSync,
  seedFromPeerUrl,
} from "./federation";
import {
  federationPeersFixture,
  federationStatusFixture,
  federationSyncFixture,
} from "../../test/fixtures";

describe("federation F6 wrappers", () => {
  it("loads status and peers", async () => {
    const status = await fetchFederationStatus();
    expect(status.did).toBe(federationStatusFixture.did);
    expect(status.followed_peer_count).toBe(1);
    expect(status.seed_peer_url).toBe("https://openhardwaremanager.org");

    const peers = await listFederationPeers();
    expect(peers).toHaveLength(federationPeersFixture.peers.length);
    expect(peers[0]?.followed).toBe(true);
  });

  it("follows a peer and runs sync", async () => {
    const followed = await followFederationPeer(federationPeersFixture.peers[0]!.did);
    expect(followed.followed).toBe(true);

    const sync = await runFederationSync("http://peer-b:8001");
    expect(sync.total_pulled).toBe(federationSyncFixture.total_pulled);
  });

  it("seedFromPeerUrl runs OKH then OKW sync", async () => {
    const result = await seedFromPeerUrl("https://openhardwaremanager.org");
    expect(result.okhPulled).toBe(federationSyncFixture.total_pulled);
    expect(result.okwPulled).toBe(federationSyncFixture.total_pulled);
  });
});
