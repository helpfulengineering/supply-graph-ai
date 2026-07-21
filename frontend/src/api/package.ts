import { get, post, ApiError } from "./client";
import { authHeader } from "../features/auth/tokenStorage";
import type {
  PackageListResponse,
  PackageBuildResponse,
  PackageBuildMetadata,
  PackageListItem,
} from "../types/package";

export function splitPackageName(packageName: string): { org: string; project: string } {
  const [org, project] = packageName.split("/");
  if (!org || !project) {
    throw new Error(`Invalid package name (expected org/project): ${packageName}`);
  }
  return { org, project };
}

export function fetchPackageList(page = 1, page_size = 50): Promise<PackageListResponse> {
  return get<PackageListResponse>("/package/list", { page, page_size });
}

/** Trigger a package build from a stored OKH manifest UUID. */
export async function buildPackageFromManifest(
  manifestId: string,
): Promise<PackageBuildMetadata> {
  const res = await post<PackageBuildResponse>(`/package/build/${manifestId}`, {});
  const meta = res.data?.metadata;
  if (!meta || typeof meta !== "object") {
    throw new Error("Invalid package build response: missing data.metadata");
  }
  return meta as PackageBuildMetadata;
}

/** Returns the download URL for a package (use with Bearer fetch, not bare &lt;a&gt;). */
export function packageDownloadUrl(packageName: string, version: string): string {
  const { org, project } = splitPackageName(packageName);
  return `/v1/api/package/${encodeURIComponent(org)}/${encodeURIComponent(project)}/${encodeURIComponent(version)}/download`;
}

export function packageDetailPath(packageName: string, version: string): string {
  const { org, project } = splitPackageName(packageName);
  return `/packages/${encodeURIComponent(org)}/${encodeURIComponent(project)}/${encodeURIComponent(version)}`;
}

export async function fetchPackageMetadata(
  org: string,
  project: string,
  version: string,
): Promise<PackageListItem> {
  const res = await get<{ data?: { metadata?: PackageListItem } }>(
    `/package/${encodeURIComponent(org)}/${encodeURIComponent(project)}/${encodeURIComponent(version)}`,
  );
  const meta = res.data?.metadata;
  if (!meta) throw new Error("Package metadata missing from response");
  return meta;
}

export async function pinPackage(
  org: string,
  project: string,
  version: string,
): Promise<void> {
  await post(
    `/package/${encodeURIComponent(org)}/${encodeURIComponent(project)}/${encodeURIComponent(version)}/pin`,
    {},
  );
}

export async function verifyPackagePin(
  org: string,
  project: string,
  version: string,
): Promise<{ verified: boolean; changed_files?: string[] }> {
  const res = await get<{ data?: { verified?: boolean; changed_files?: string[] } }>(
    `/package/${encodeURIComponent(org)}/${encodeURIComponent(project)}/${encodeURIComponent(version)}/verify-pin`,
  );
  return {
    verified: Boolean(res.data?.verified),
    changed_files: res.data?.changed_files,
  };
}

function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

async function blobFromResponse(res: Response): Promise<Blob> {
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string; message?: string };
      message = body.message ?? (typeof body.detail === "string" ? body.detail : message);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, message);
  }
  return res.blob();
}

/** Download one package tarball with Bearer auth and save to disk. */
export async function downloadPackageFile(
  packageName: string,
  version: string,
): Promise<void> {
  const { org, project } = splitPackageName(packageName);
  const res = await fetch(packageDownloadUrl(packageName, version), {
    headers: { ...authHeader() },
  });
  const blob = await blobFromResponse(res);
  saveBlob(blob, `${org}-${project}-${version}.tar.gz`);
}

export type PackageZipItem = { org: string; project: string; version: string };

/** POST /package/download-zip → save ohm-packages.zip */
export async function downloadPackagesZip(items: PackageZipItem[]): Promise<void> {
  const res = await fetch("/v1/api/package/download-zip", {
    method: "POST",
    headers: {
      Accept: "application/zip",
      "Content-Type": "application/json",
      ...authHeader(),
    },
    body: JSON.stringify({ items }),
  });
  const blob = await blobFromResponse(res);
  saveBlob(blob, "ohm-packages.zip");
}
