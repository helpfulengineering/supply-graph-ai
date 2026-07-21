import { useNavigate } from "react-router-dom";
import { downloadPackageFile, packageDetailPath } from "../../api/package";
import type { PackageListItem } from "../../types/package";
import { useAuth } from "../../context/AuthContext";
import { Button } from "../../components/ui/button";

interface Props {
  pkg: PackageListItem;
  selected?: boolean;
  onToggle?: () => void;
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

export function PackageCard({ pkg, selected = false, onToggle }: Props) {
  const navigate = useNavigate();
  const { reportAuthFailure } = useAuth();
  const detail = packageDetailPath(pkg.package_name, pkg.version);

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900 sm:flex-row sm:items-start sm:justify-between">
      <div className="flex min-w-0 gap-3">
        {onToggle && (
          <input
            type="checkbox"
            className="mt-1"
            checked={selected}
            onChange={onToggle}
            aria-label={`Select ${pkg.package_name} ${pkg.version}`}
          />
        )}
        <div className="min-w-0 space-y-2">
          <button type="button" className="text-left" onClick={() => navigate(detail)}>
            <h3 className="font-semibold text-slate-800 break-all hover:text-indigo-600 dark:text-slate-100">
              {pkg.package_name}
            </h3>
            <p className="font-mono text-xs text-slate-600 dark:text-slate-400">v{pkg.version}</p>
          </button>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600 dark:text-slate-400">
            <span>
              {pkg.total_files} file{pkg.total_files !== 1 ? "s" : ""}
            </span>
            <span>{formatBytes(pkg.total_size_bytes)}</span>
            <span>Built {formatDate(pkg.build_timestamp)}</span>
            {pkg.okh_manifest_id && (
              <span className="font-mono">manifest: {pkg.okh_manifest_id.slice(0, 8)}…</span>
            )}
          </div>
        </div>
      </div>

      <Button
        type="button"
        className="shrink-0"
        onClick={() =>
          void downloadPackageFile(pkg.package_name, pkg.version).catch(reportAuthFailure)
        }
      >
        ↓ Download .tar.gz
      </Button>
    </div>
  );
}
