import { get, post } from "./client";
import type { PackageListResponse, PackageBuildResponse } from "../types/package";

export function fetchPackageList(page = 1, page_size = 50): Promise<PackageListResponse> {
  return get<PackageListResponse>("/package/list", { page, page_size });
}

/** Trigger a package build from a stored OKH manifest UUID. */
export function buildPackageFromManifest(
  manifestId: string
): Promise<PackageBuildResponse> {
  return post<PackageBuildResponse>(`/package/build/${manifestId}`, {});
}

/** Returns the download URL for a package (triggers browser download). */
export function packageDownloadUrl(packageName: string, version: string): string {
  // packageName may contain a slash (e.g. "org/repo") — encode each segment
  // so they pass through as URL path components.
  const encoded = packageName.split("/").map(encodeURIComponent).join("/");
  return `/v1/api/package/${encoded}/${encodeURIComponent(version)}/download`;
}
