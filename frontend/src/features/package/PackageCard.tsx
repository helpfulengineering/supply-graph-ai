import { packageDownloadUrl } from "../../api/package";
import type { PackageListItem } from "../../types/package";

interface Props {
  pkg: PackageListItem;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function PackageCard({ pkg }: Props) {
  const downloadUrl = packageDownloadUrl(pkg.package_name, pkg.version);

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md dark:border-slate-700 dark:bg-slate-900 sm:flex-row sm:items-start sm:justify-between">
      {/* Left: identity + metadata */}
      <div className="min-w-0 space-y-2">
        <div>
          <h3 className="font-semibold text-slate-800 dark:text-slate-100 break-all">
            {pkg.package_name}
          </h3>
          <p className="font-mono text-xs text-slate-400 dark:text-slate-500">
            v{pkg.version}
          </p>
        </div>

        {/* Stats row */}
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
          <span>{pkg.total_files} file{pkg.total_files !== 1 ? "s" : ""}</span>
          <span>{formatBytes(pkg.total_size_bytes)}</span>
          <span>Built {formatDate(pkg.build_timestamp)}</span>
          {pkg.okh_manifest_id && (
            <span className="font-mono">
              manifest: {pkg.okh_manifest_id.slice(0, 8)}…
            </span>
          )}
        </div>

        {/* File inventory hint */}
        <p className="text-xs text-slate-400 italic dark:text-slate-500">
          Tarball archive — download for local inspection of all design files.
        </p>
      </div>

      {/* Right: download action */}
      <div className="flex shrink-0 items-start gap-2">
        <a
          href={downloadUrl}
          download
          className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors dark:bg-emerald-500 dark:hover:bg-emerald-400"
        >
          ↓ Download .tar.gz
        </a>
      </div>
    </div>
  );
}
