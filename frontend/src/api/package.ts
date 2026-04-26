import { get, post } from "./client";
import type {
  PackageListResponse,
  PackageBuildResponse,
  PackageBuildMetadata,
} from "../types/package";

export function fetchPackageList(page = 1, page_size = 50): Promise<PackageListResponse> {
  return get<PackageListResponse>("/package/list", { page, page_size });
}

/** Trigger a package build from a stored OKH manifest UUID. */
export async function buildPackageFromManifest(
  manifestId: string
): Promise<PackageBuildMetadata> {
  const res = await post<PackageBuildResponse>(`/package/build/${manifestId}`, {});
  const meta = res.data?.metadata;
  if (!meta || typeof meta !== "object") {
    throw new Error("Invalid package build response: missing data.metadata");
  }
  return meta as PackageBuildMetadata;
}

/** Returns the download URL for a package (triggers browser download). */
export function packageDownloadUrl(packageName: string, version: string): string {
  // packageName may contain a slash (e.g. "org/repo") — encode each segment
  // so they pass through as URL path components.
  const encoded = packageName.split("/").map(encodeURIComponent).join("/");
  return `/v1/api/package/${encoded}/${encodeURIComponent(version)}/download`;
}
