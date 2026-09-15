import { API_PREFIX, post } from "./client";
import { authHeader } from "../features/auth/tokenStorage";
import type { RFQGenerateRequest, RFQGenerateResponse } from "../types/rfq";

export function generateRfq(
  request: RFQGenerateRequest
): Promise<RFQGenerateResponse> {
  return post<RFQGenerateResponse>("/rfq/generate", request);
}

export interface PackageBuildResult {
  status: string;
  data: {
    metadata: {
      package_name: string;
      version: string;
      [key: string]: unknown;
    };
  };
}

export function buildPackage(manifestId: string): Promise<PackageBuildResult> {
  return post<PackageBuildResult>(`/package/build/${manifestId}`, {});
}

/**
 * Download the RFQ documents and the design package as one zip.
 *
 * The thing a coordinator actually sends: one RFQ per workshop, plus the design
 * they refer to, ready to attach to an email. Nothing in the documents points
 * back at OHM, because the recipient has never heard of it.
 *
 * Returns the blob and the server's filename, which names the design and the
 * date — two bundles a week apart are meant to be distinguishable in a
 * downloads folder.
 */
export async function downloadRfqBundle(
  request: RFQGenerateRequest,
): Promise<{ blob: Blob; filename: string }> {
  const res = await fetch(`${API_PREFIX}/rfq/bundle`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    throw new Error(
      res.status === 401
        ? "Sign in to download the bundle — building a design package needs write access."
        : `Could not build the bundle (HTTP ${res.status}).`,
    );
  }
  const match = /filename="([^"]+)"/.exec(
    res.headers.get("content-disposition") ?? "",
  );
  return { blob: await res.blob(), filename: match?.[1] ?? "rfq-bundle.zip" };
}
