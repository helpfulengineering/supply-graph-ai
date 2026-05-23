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
  // API route is /{org}/{project}/{version}/download — split org/project for path segments.
  const [org, project] = packageName.split("/");
  if (!org || !project) {
    throw new Error(`Invalid package name (expected org/project): ${packageName}`);
  }
  return `/v1/api/package/${encodeURIComponent(org)}/${encodeURIComponent(project)}/${encodeURIComponent(version)}/download`;
}
