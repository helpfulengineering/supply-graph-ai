import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchPackageList, packageDetailPath } from "../../api/package";

/** Packages built from this OKH manifest (client-filtered list). */
export function ReleasesStrip({ okhId }: { okhId: string }) {
  const list = useQuery({
    queryKey: ["package-list"],
    queryFn: () => fetchPackageList(1, 100),
    staleTime: 60_000,
  });

  const releases = useMemo(
    () =>
      (list.data?.items ?? []).filter((p) => p.okh_manifest_id === okhId),
    [list.data, okhId],
  );

  if (list.isLoading) {
    return (
      <p className="text-sm text-muted-foreground">Loading releases…</p>
    );
  }
  if (!releases.length) return null;

  return (
    <section
      aria-labelledby="releases-heading"
      className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
    >
      <h2
        id="releases-heading"
        className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500"
      >
        Package releases
      </h2>
      <ul className="space-y-2">
        {releases.map((p) => (
          <li key={`${p.package_name}@${p.version}`}>
            <Link
              to={packageDetailPath(p.package_name, p.version)}
              className="text-sm text-indigo-600 hover:underline dark:text-indigo-400"
            >
              {p.package_name}
              <span className="ml-2 font-mono text-xs text-slate-500">v{p.version}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
