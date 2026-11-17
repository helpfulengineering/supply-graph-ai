/**
 * The two-node federation stack from docker-compose.federation.yml.
 *
 * Peer A is on 8001 with key fed-test-key-a; peer B on 8002 with fed-test-key-b.
 * From the host, those are localhost. Peer B reaches A at ohm-peer-a:8001 over
 * the compose network, so a subscription names that URL, not localhost.
 */
export const PEER_A = process.env.UAT_PEER_A_URL ?? "http://localhost:8001";
export const PEER_B = process.env.UAT_PEER_B_URL ?? "http://localhost:8002";
export const KEY_A = process.env.UAT_KEY_A ?? "fed-test-key-a";
export const KEY_B = process.env.UAT_KEY_B ?? "fed-test-key-b";
/** How peer B's container reaches peer A. */
export const PEER_A_INTERNAL =
  process.env.UAT_PEER_A_INTERNAL ?? "http://ohm-peer-a:8001";
