import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  downloadPackageFile,
  fetchPackageMetadata,
  pinPackage,
  splitPackageName,
  verifyPackagePin,
} from "../../api/package";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { Button } from "../../components/ui/button";
import { useAuth } from "../../context/AuthContext";

interface Props {
  org: string;
  project: string;
  version: string;
}

export function PackageDetailView({ org, project, version }: Props) {
  const { reportAuthFailure } = useAuth();
  const queryClient = useQueryClient();
  const packageName = `${org}/${project}`;

  const meta = useQuery({
    queryKey: ["package", org, project, version],
    queryFn: () => fetchPackageMetadata(org, project, version),
  });

  const pin = useMutation({
    mutationFn: () => pinPackage(org, project, version),
    onError: reportAuthFailure,
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["package", org, project, version] }),
  });

  const verify = useMutation({
    mutationFn: () => verifyPackagePin(org, project, version),
    onError: reportAuthFailure,
  });

  if (meta.isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-foreground break-all">{packageName}</h1>
        <LoadingSpinner message="Loading package…" />
      </div>
    );
  }
  if (meta.isError || !meta.data) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-foreground break-all">{packageName}</h1>
        <ErrorMessage error={meta.error ?? new Error("Package not found")} />
      </div>
    );
  }
  const pkg = meta.data;

  return (
    <div className="space-y-6">
      <nav className="flex items-center gap-2 text-sm text-slate-500">
        <Link to="/packages" className="hover:text-indigo-600">
          Packages
        </Link>
        <span aria-hidden="true">›</span>
        <span className="truncate text-slate-700 dark:text-slate-200">
          {packageName}@{version}
        </span>
      </nav>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground break-all">{packageName}</h1>
          <p className="mt-1 font-mono text-sm text-muted-foreground">v{pkg.version}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            onClick={() =>
              void downloadPackageFile(packageName, version).catch(reportAuthFailure)
            }
          >
            ↓ Download .tar.gz
          </Button>
          <Button variant="outline" disabled={pin.isPending} onClick={() => pin.mutate()}>
            {pin.isPending ? "Pinning…" : "Pin"}
          </Button>
          <Button
            variant="outline"
            disabled={verify.isPending}
            onClick={() => verify.mutate()}
          >
            {verify.isPending ? "Verifying…" : "Verify pin"}
          </Button>
        </div>
      </div>

      <dl className="grid gap-3 rounded-xl border border-slate-200 bg-white p-5 text-sm dark:border-slate-700 dark:bg-slate-900 sm:grid-cols-2">
        <div>
          <dt className="text-xs uppercase text-slate-500">Files</dt>
          <dd>{pkg.total_files}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase text-slate-500">Size</dt>
          <dd>{pkg.total_size_bytes.toLocaleString()} bytes</dd>
        </div>
        <div>
          <dt className="text-xs uppercase text-slate-500">Built</dt>
          <dd>{pkg.build_timestamp}</dd>
        </div>
        {pkg.okh_manifest_id && (
          <div>
            <dt className="text-xs uppercase text-slate-500">OKH manifest</dt>
            <dd>
              <Link
                className="font-mono text-indigo-600 hover:underline"
                to={`/okh/${pkg.okh_manifest_id}`}
              >
                {pkg.okh_manifest_id}
              </Link>
            </dd>
          </div>
        )}
      </dl>

      {pin.isSuccess && (
        <p className="text-sm text-emerald-700 dark:text-emerald-400" role="status">
          Package pinned.
        </p>
      )}
      {verify.isSuccess && (
        <p
          className={`text-sm ${verify.data.verified ? "text-emerald-700" : "text-amber-700"}`}
          role="status"
        >
          {verify.data.verified
            ? "Pin verified — contents unchanged."
            : `Pin drift: ${(verify.data.changed_files ?? []).join(", ") || "files changed"}`}
        </p>
      )}
      {(pin.isError || verify.isError) && (
        <p className="text-sm text-red-600" role="alert">
          {(pin.error ?? verify.error) instanceof Error
            ? ((pin.error ?? verify.error) as Error).message
            : "Action failed."}
        </p>
      )}
    </div>
  );
}

/** Parse route params; returns null if invalid. */
export function parsePackageRoute(
  org?: string,
  project?: string,
  version?: string,
): Props | null {
  if (!org || !project || !version) return null;
  try {
    splitPackageName(`${decodeURIComponent(org)}/${decodeURIComponent(project)}`);
  } catch {
    return null;
  }
  return {
    org: decodeURIComponent(org),
    project: decodeURIComponent(project),
    version: decodeURIComponent(version),
  };
}
