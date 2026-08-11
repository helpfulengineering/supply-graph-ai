"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { fetchPackageList, packageDetailPath } from "../../api/package";

/** Packages built from this OKH manifest (client-filtered list). */
export function ReleasesStrip({ okhId }: { okhId: string }) {
  const list = useQuery({
    queryKey: ["package-list"],
    queryFn: () => fetchPackageList(1, 100),
    staleTime: 60_000,
  });

  const releases = useMemo(
    () => (list.data?.items ?? []).filter((p) => p.okh_manifest_id === okhId),
    [list.data, okhId],
  );

  if (list.isLoading) {
    return <p className="text-sm text-muted-foreground">Loading releases…</p>;
  }
  if (!releases.length) return null;

  return (
    <section
      aria-labelledby="releases-heading"
      className="rounded-xl border border-border bg-card p-5"
    >
      <h2
        id="releases-heading"
        className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground"
      >
        Package releases
      </h2>
      <ul className="space-y-2">
        {releases.map((p) => (
          <li key={`${p.package_name}@${p.version}`}>
            <Link
              href={packageDetailPath(p.package_name, p.version)}
              className="text-sm text-primary hover:underline"
            >
              {p.package_name}
              <span className="ml-2 font-mono text-xs text-muted-foreground">
                v{p.version}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
