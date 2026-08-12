"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchSolutionHierarchy } from "@/api/ohm/supply-tree";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { PANEL, PANEL_BODY } from "@/components/ui/surface";
import { BODY_MUTED, CAPTION, STAT_VALUE } from "@/components/ui/typography";
import { cn } from "@/lib/utils";

/**
 * What this solution is made of.
 *
 * The one supply-tree read that adds something: the visualization bundle
 * carries the production sequence, the dependency graph and the KPIs, and no
 * component parent/child structure at all — so "how deep does this go, and
 * what are the roots" was a question the page could not answer.
 *
 * Silent when the endpoint is unavailable. The graph above is the page; a node
 * that cannot answer this should cost a panel, not the view.
 */
export function ComponentsPanel({ solutionId }: { solutionId: string }) {
  const query = useQuery({
    queryKey: ["solution-hierarchy", solutionId],
    queryFn: () => fetchSolutionHierarchy(solutionId),
    retry: false,
    retryOnMount: false,
  });

  if (query.isError) return null;

  const summary = query.data?.summary ?? {};
  const roots = query.data?.root_components ?? [];

  return (
    <section aria-labelledby="components" className={cn(PANEL, PANEL_BODY)}>
      <SectionHeading id="components" role="card">
        Components
      </SectionHeading>

      {query.isPending ? (
        <p className={cn(CAPTION, "mt-2")}>Reading the hierarchy…</p>
      ) : (
        <>
          <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ["Components", summary.total_components],
              ["Roots", summary.root_components],
              ["Trees", summary.total_trees],
              ["Max depth", summary.max_depth],
            ].map(([label, value]) => (
              <div key={String(label)}>
                <dt className={CAPTION}>{label}</dt>
                <dd className={cn(STAT_VALUE, "mt-1")}>{value ?? 0}</dd>
              </div>
            ))}
          </dl>

          {roots.length === 0 ? (
            <p className={cn(BODY_MUTED, "mt-3")}>
              No root components — every part of this solution depends on
              something else, which usually means the tree is cyclic.
            </p>
          ) : (
            <div className="mt-4">
              <p className={CAPTION}>Starts from</p>
              <ul className="mt-1 space-y-0.5">
                {roots.map((root) => (
                  <li key={root} className="text-sm text-foreground">
                    {root}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  );
}
