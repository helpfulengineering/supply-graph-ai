/**
 * Federation API wrappers (Track F — F6).
 */
import { apiClient, ApiError, errorMessage, requestIdFromError } from "./client";
import type { components } from "../generated/schema";

export type FederationStatus = components["schemas"]["FederationStatusResponse"];
export type PeerState = components["schemas"]["PeerState"];
export type SyncRunResponse = components["schemas"]["SyncRunResponse"];
export type FollowResponse = components["schemas"]["FollowResponse"];

export async function fetchFederationStatus(): Promise<FederationStatus> {
  const { data, error, response } = await apiClient.GET("/api/federation/status");
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to load federation status"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export async function listFederationPeers(): Promise<PeerState[]> {
  const { data, error, response } = await apiClient.GET("/api/federation/peers");
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
  const { data, error, response } = await apiClient.POST("/api/federation/peers/discover");
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to discover peers"),
      requestIdFromError(error, response),
    );
  }
  return data.peers;
}

export async function followFederationPeer(did: string): Promise<FollowResponse> {
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

export async function unfollowFederationPeer(did: string): Promise<FollowResponse> {
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

export async function runFederationSync(peerUrl?: string): Promise<SyncRunResponse> {
  const { data, error, response } = await apiClient.POST("/api/federation/sync/run", {
    params: { query: peerUrl ? { peer_url: peerUrl } : {} },
  });
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to run federation sync"),
      requestIdFromError(error, response),
    );
  }
  return data;
}
