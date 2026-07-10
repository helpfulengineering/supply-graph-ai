import { zipSync } from "fflate";
import type { OkhFileRef, OkhManifest } from "../../types/okh";
import { okhFileHref } from "../okh/okhFileHref";
import { fileBasename, normalizeDisplayPath } from "../okh/okhFilePath";

/** Minimal File System Access API typings (not in all TS DOM libs). */
interface DirectoryPickerOptions {
  id?: string;
  mode?: "read" | "readwrite";
  startIn?: "desktop" | "documents" | "downloads" | "music" | "pictures" | "videos";
}

type ShowDirectoryPickerFn = (
  options?: DirectoryPickerOptions,
) => Promise<FileSystemDirectoryHandle>;

function getShowDirectoryPicker(): ShowDirectoryPickerFn | undefined {
  const w = window as Window & { showDirectoryPicker?: ShowDirectoryPickerFn };
  return typeof w.showDirectoryPicker === "function" ? w.showDirectoryPicker.bind(w) : undefined;
}

export type LocalPackageStatus = "idle" | "building" | "done" | "partial" | "error" | "cancelled";

export interface LocalPackageFileFailure {
  path: string;
  reason: string;
}

export interface LocalPackageResult {
  status: Exclude<LocalPackageStatus, "idle" | "building">;
  packageName: string;
  written: number;
  failed: LocalPackageFileFailure[];
  message: string;
}

export interface LocalPackageInput {
  okh: Pick<
    OkhManifest,
    | "id"
    | "title"
    | "version"
    | "design_files"
    | "manufacturing_files"
    | "making_instructions"
  > &
    Partial<OkhManifest>;
}

/** Safe folder / zip basename from title + version. */
export function packageFolderName(title: string, version: string | null | undefined): string {
  const base = (title || "okh-package")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
  const ver = (version || "unversioned")
    .trim()
    .replace(/[^a-zA-Z0-9._-]+/g, "-")
    .slice(0, 32);
  return `${base || "okh-package"}-${ver}`;
}

function collectFiles(okh: LocalPackageInput["okh"]): OkhFileRef[] {
  return [
    ...(okh.design_files ?? []),
    ...(okh.manufacturing_files ?? []),
    ...(okh.making_instructions ?? []),
  ];
}

/** Unique relative paths for package layout (collision-safe). */
export function packageRelativePath(file: OkhFileRef, used: Set<string>): string {
  let rel = normalizeDisplayPath(file.path) || fileBasename(file.path);
  rel = rel.replace(/^\/+/, "");
  if (!rel || rel === ".") {
    rel = fileBasename(file.path) || "file";
  }
  if (!used.has(rel)) {
    used.add(rel);
    return rel;
  }
  const dot = rel.lastIndexOf(".");
  const stem = dot > 0 ? rel.slice(0, dot) : rel;
  const ext = dot > 0 ? rel.slice(dot) : "";
  let i = 2;
  let candidate = `${stem}-${i}${ext}`;
  while (used.has(candidate)) {
    i += 1;
    candidate = `${stem}-${i}${ext}`;
  }
  used.add(candidate);
  return candidate;
}

async function fetchFileBytes(okhId: string, file: OkhFileRef): Promise<Uint8Array> {
  const href = okhFileHref(okhId, file);
  const res = await fetch(href);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} fetching ${file.path}`);
  }
  return new Uint8Array(await res.arrayBuffer());
}

async function ensureSubdir(
  root: FileSystemDirectoryHandle,
  relativePath: string,
): Promise<{ dir: FileSystemDirectoryHandle; fileName: string }> {
  const parts = relativePath.split("/").filter(Boolean);
  if (parts.length === 0) {
    throw new Error("Invalid empty file path");
  }
  const fileName = parts[parts.length - 1]!;
  let dir = root;
  for (const segment of parts.slice(0, -1)) {
    dir = await dir.getDirectoryHandle(segment, { create: true });
  }
  return { dir, fileName };
}

async function writeBytes(
  dir: FileSystemDirectoryHandle,
  fileName: string,
  bytes: Uint8Array,
): Promise<void> {
  const handle = await dir.getFileHandle(fileName, { create: true });
  const writable = await handle.createWritable();
  try {
    await writable.write(bytes);
  } finally {
    await writable.close();
  }
}

function manifestJson(okh: LocalPackageInput["okh"]): Uint8Array {
  const text = JSON.stringify(okh, null, 2);
  return new TextEncoder().encode(text);
}

function readmeText(
  packageName: string,
  written: number,
  failed: LocalPackageFileFailure[],
): string {
  const lines = [
    `OKH local package: ${packageName}`,
    `Built: ${new Date().toISOString()}`,
    "",
    "Contents:",
    "- okh-manifest.json — full OKH manifest snapshot",
    "- files/ — design, manufacturing, and instruction files",
    "",
    `Files written: ${written}`,
  ];
  if (failed.length > 0) {
    lines.push(`Files failed: ${failed.length}`);
    for (const f of failed) {
      lines.push(`  - ${f.path}: ${f.reason}`);
    }
  }
  return lines.join("\n");
}

async function buildIntoDirectory(
  parent: FileSystemDirectoryHandle,
  input: LocalPackageInput,
): Promise<LocalPackageResult> {
  const { okh } = input;
  const packageName = packageFolderName(okh.title, okh.version);
  let packageDir: FileSystemDirectoryHandle;
  try {
    packageDir = await parent.getDirectoryHandle(packageName, { create: true });
  } catch (e) {
    const reason = e instanceof Error ? e.message : String(e);
    return {
      status: "error",
      packageName,
      written: 0,
      failed: [],
      message: `Cannot create package directory "${packageName}": ${reason}. Check that you granted write access to the selected folder.`,
    };
  }

  let filesDir: FileSystemDirectoryHandle;
  try {
    filesDir = await packageDir.getDirectoryHandle("files", { create: true });
  } catch (e) {
    const reason = e instanceof Error ? e.message : String(e);
    return {
      status: "error",
      packageName,
      written: 0,
      failed: [],
      message: `Cannot create files/ subdirectory: ${reason}`,
    };
  }

  try {
    await writeBytes(packageDir, "okh-manifest.json", manifestJson(okh));
  } catch (e) {
    const reason = e instanceof Error ? e.message : String(e);
    return {
      status: "error",
      packageName,
      written: 0,
      failed: [],
      message: `Cannot write okh-manifest.json: ${reason}`,
    };
  }

  const files = collectFiles(okh);
  const used = new Set<string>();
  const failed: LocalPackageFileFailure[] = [];
  let written = 0;

  for (const file of files) {
    const rel = packageRelativePath(file, used);
    try {
      const bytes = await fetchFileBytes(okh.id, file);
      const { dir, fileName } = await ensureSubdir(filesDir, rel);
      await writeBytes(dir, fileName, bytes);
      written += 1;
    } catch (e) {
      failed.push({
        path: rel,
        reason: e instanceof Error ? e.message : String(e),
      });
    }
  }

  try {
    await writeBytes(
      packageDir,
      "PACKAGE.txt",
      new TextEncoder().encode(readmeText(packageName, written, failed)),
    );
  } catch {
    // Non-fatal
  }

  if (written === 0 && files.length > 0) {
    return {
      status: "error",
      packageName,
      written,
      failed,
      message: `Created ${packageName}/ but could not download any of ${files.length} files. Check that the API file proxy is reachable.`,
    };
  }

  if (failed.length > 0) {
    return {
      status: "partial",
      packageName,
      written,
      failed,
      message: `Wrote ${written} file(s) to ${packageName}/; ${failed.length} failed (see PACKAGE.txt).`,
    };
  }

  return {
    status: "done",
    packageName,
    written,
    failed,
    message: `Package written to ${packageName}/ (${written} file(s)).`,
  };
}

async function buildAsZipDownload(input: LocalPackageInput): Promise<LocalPackageResult> {
  const { okh } = input;
  const packageName = packageFolderName(okh.title, okh.version);
  const files = collectFiles(okh);
  const used = new Set<string>();
  const failed: LocalPackageFileFailure[] = [];
  const entries: Record<string, Uint8Array> = {
    [`${packageName}/okh-manifest.json`]: manifestJson(okh),
  };
  let written = 0;

  for (const file of files) {
    const rel = packageRelativePath(file, used);
    try {
      const bytes = await fetchFileBytes(okh.id, file);
      entries[`${packageName}/files/${rel}`] = bytes;
      written += 1;
    } catch (e) {
      failed.push({
        path: rel,
        reason: e instanceof Error ? e.message : String(e),
      });
    }
  }

  entries[`${packageName}/PACKAGE.txt`] = new TextEncoder().encode(
    readmeText(packageName, written, failed),
  );

  if (written === 0 && files.length > 0) {
    return {
      status: "error",
      packageName,
      written,
      failed,
      message: `Could not download any of ${files.length} files for the zip. Check that the API file proxy is reachable.`,
    };
  }

  const zipped = zipSync(entries, { level: 6 });
  const blob = new Blob([new Uint8Array(zipped)], { type: "application/zip" });
  const url = URL.createObjectURL(blob);
  try {
    const a = document.createElement("a");
    a.href = url;
    a.download = `${packageName}.zip`;
    a.click();
  } finally {
    URL.revokeObjectURL(url);
  }

  if (failed.length > 0) {
    return {
      status: "partial",
      packageName,
      written,
      failed,
      message: `Downloaded ${packageName}.zip with ${written} file(s); ${failed.length} failed.`,
    };
  }

  return {
    status: "done",
    packageName,
    written,
    failed,
    message: `Downloaded ${packageName}.zip (${written} file(s)).`,
  };
}

/**
 * Build an OKH package on the user's machine.
 *
 * Preferred: directory picker → create `<title>-<version>/` with manifest + files/.
 * Fallback (no File System Access API): assemble a .zip and trigger download.
 */
export async function buildLocalOkhPackage(
  input: LocalPackageInput,
): Promise<LocalPackageResult> {
  if (!input.okh?.id) {
    return {
      status: "error",
      packageName: "okh-package",
      written: 0,
      failed: [],
      message: "Missing OKH manifest id — cannot build package.",
    };
  }

  const showDirectoryPicker = getShowDirectoryPicker();
  if (showDirectoryPicker) {
    let parent: FileSystemDirectoryHandle;
    try {
      parent = await showDirectoryPicker({
        id: "okh-package-export",
        mode: "readwrite",
        startIn: "downloads",
      });
    } catch (e) {
      const name = e instanceof DOMException ? e.name : "";
      if (name === "AbortError") {
        return {
          status: "cancelled",
          packageName: packageFolderName(input.okh.title, input.okh.version),
          written: 0,
          failed: [],
          message: "Package build cancelled.",
        };
      }
      // Permission / unsupported quirks → zip fallback
      return buildAsZipDownload(input);
    }

    // Probe write access before downloading everything
    try {
      const probe = await parent.getFileHandle(".ohm-write-probe", { create: true });
      const w = await probe.createWritable();
      await w.write("ok");
      await w.close();
      await parent.removeEntry(".ohm-write-probe");
    } catch (e) {
      const reason = e instanceof Error ? e.message : String(e);
      return {
        status: "error",
        packageName: packageFolderName(input.okh.title, input.okh.version),
        written: 0,
        failed: [],
        message: `Selected folder is not writable: ${reason}. Choose another folder or use a browser that supports folder export (Chrome/Edge).`,
      };
    }

    return buildIntoDirectory(parent, input);
  }

  return buildAsZipDownload(input);
}
