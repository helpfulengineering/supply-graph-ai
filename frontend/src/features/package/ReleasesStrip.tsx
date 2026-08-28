"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { fetchPackageList, packageDetailPath } from "../../api/package";
import { PANEL } from "../../components/ui/surface";
import { SECTION_LABEL } from "../../components/ui/typography";
import { cn } from "@/lib/utils";

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
    <section aria-labelledby="releases-heading" className={PANEL}>
      <h2 id="releases-heading" className={cn(SECTION_LABEL, "mb-3")}>
        Package releases
      </h2>
      <ul className="space-y-2">
        {releases.map((p) => (
          <li key={`${p.package_name}@${p.version}`}>
            {/* inline-flex + min-h-6 so the release clears the 24x24 WCAG
                2.5.8 minimum: it is the only thing in its <li>, so 2.5.8's
                inline exception does not apply and the text's 18px line box
                is the whole target. */}
            <Link
              href={packageDetailPath(p.package_name, p.version)}
              className="inline-flex min-h-6 items-center text-sm text-primary-ink hover:underline"
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
