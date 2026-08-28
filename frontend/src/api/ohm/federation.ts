/**
 * Federation API wrappers (Track F — F6).
 */
import {
  apiClient,
  ApiError,
  errorMessage,
  requestIdFromError,
} from "./client";
import type { components } from "../generated/schema";

export type FederationStatus =
  components["schemas"]["FederationStatusResponse"];
export type PeerState = components["schemas"]["PeerState"];
export type SyncRunResponse = components["schemas"]["SyncRunResponse"];
export type FollowResponse = components["schemas"]["FollowResponse"];

export async function fetchFederationStatus(): Promise<FederationStatus> {
  const { data, error, response } = await apiClient.GET(
    "/api/federation/status",
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to load federation status"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

/**
 * The one query options both federation surfaces share.
 *
 * `/api/federation/status` answers 404 with "Federation is not enabled" by
 * design — `require_federation_api` in the backend raises it whenever the
 * service is off, which is the default and therefore most instances. That is
 * an answer, not a fault, and the UI reads it as one: the Network CTA hides
 * itself and the Settings panel explains how to turn federation on.
 *
 * What it was not doing is remembering. React Query refetches a query in an
 * error state on every mount (`retryOnMount` defaults to true), so the
 * dashboard re-asked a question it had already been answered every time
 * somebody navigated back to it, and each one printed a red 404 in the
 * console of a production instance that is behaving exactly as configured.
 *
 * The site layer already solved this shape — see lib/site/stack.ts, which goes
 * dormant after the first PGRST202 rather than 404ing "once per page view,
 * forever". This is the same conclusion via React Query's own cache: ask once,
 * hold the answer for the session, and let an explicit invalidation after a
 * federation mutation be what refreshes it.
 *
 * The request itself cannot be avoided from here — the only way to learn
 * whether an instance federates is to ask it — so one 404 per session is the
 * floor until the API grows a capabilities probe.
 */
export const federationStatusQuery = {
  queryKey: ["federation", "status"] as const,
  queryFn: fetchFederationStatus,
  retry: false,
  retryOnMount: false,
  refetchOnWindowFocus: false,
  staleTime: Infinity,
};

export async function listFederationPeers(): Promise<PeerState[]> {
  const { data, error, response } = await apiClient.GET(
    "/api/federation/peers",
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to list federation peers"),
      requestIdFromError(error, response),
    );
  }
  return data.peers;
}

export async function discoverFederationPeers(): Promise<PeerState[]> {
  const { data, error, response } = await apiClient.POST(
    "/api/federation/peers/discover",
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to discover peers"),
      requestIdFromError(error, response),
    );
  }
  return data.peers;
}

export async function followFederationPeer(
  did: string,
): Promise<FollowResponse> {
  const { data, error, response } = await apiClient.POST(
    "/api/federation/peers/{did}/follow",
    { params: { path: { did } } },
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to follow peer"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export async function unfollowFederationPeer(
  did: string,
): Promise<FollowResponse> {
  const { data, error, response } = await apiClient.DELETE(
    "/api/federation/peers/{did}/follow",
    { params: { path: { did } } },
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to unfollow peer"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export async function runFederationSync(
  peerUrl?: string,
): Promise<SyncRunResponse> {
  const { data, error, response } = await apiClient.POST(
    "/api/federation/sync/run",
    {
      params: { query: peerUrl ? { peer_url: peerUrl } : {} },
    },
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to run federation sync"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

/** Sync OKW catalog records from followed peers (after follow / seed). */
export async function runOkwFederationSync(): Promise<SyncRunResponse> {
  const { data, error, response } = await apiClient.POST(
    "/api/federation/okw/sync/run",
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to sync OKW from peers"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

/** Follow seed peer URL (identify + follow + OKH sync) then pull OKW facilities. */
export async function seedFromPeerUrl(seedPeerUrl: string): Promise<{
  okhPulled: number;
  okwPulled: number;
}> {
  const okh = await runFederationSync(seedPeerUrl);
  const okw = await runOkwFederationSync();
  return {
    okhPulled: okh.total_pulled ?? 0,
    okwPulled: okw.total_pulled ?? 0,
  };
}

export interface PackageFetchResult {
  /** "fetched" | "rebuilt" | "local" — what actually happened. */
  action: string;
  bundle_hash?: string | null;
  detail?: string | null;
  message: string;
}

/**
 * Pull a package from a peer into this node.
 *
 * The one federation endpoint that is not peer protocol: it takes a peer URL
 * and a bundle hash, requires write, and moves bytes INWARD. Everything else
 * under /api/federation is what another node calls on us.
 */
export async function fetchPeerPackage(params: {
  peerUrl: string;
  bundleHash: string;
  manifestId?: string;
  allowRebuild: boolean;
}): Promise<PackageFetchResult> {
  const { data, error, response } = await apiClient.POST(
    "/api/federation/packages/fetch",
    {
      body: {
        peer_url: params.peerUrl,
        bundle_hash: params.bundleHash,
        manifest_id: params.manifestId ?? null,
        allow_rebuild: params.allowRebuild,
      },
    },
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Fetch failed (HTTP ${response.status})`),
    );
  }
  return data as PackageFetchResult;
}

/** The `action` field as a sentence. It is the whole result. */
export function packageFetchSentence(result: PackageFetchResult): string {
  if (result.action === "local") return "Already present on this node.";
  if (result.action === "rebuilt") return "Rebuilt from the peer's manifest.";
  if (result.action === "fetched") return "Fetched from the peer.";
  return result.message;
}
