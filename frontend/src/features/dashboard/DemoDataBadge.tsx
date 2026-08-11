"use client";

import { useQuery } from "@tanstack/react-query";
import { FlaskConical } from "lucide-react";
import { fetchOkhList } from "../../api/ohm/okh";
import { demoModeEnabled } from "../../lib/demo/demoMode";

/**
 * "Demo data" indicator.
 *
 * Derived from the records themselves, not from a build flag: seed_demo_data.py
 * stamps metadata.demo on everything it writes, so this tells the truth about
 * what is loaded rather than what someone configured. A demo instance that got
 * real records stops claiming to be a demo, and a production instance cannot
 * accidentally advertise itself as one.
 *
 * Renders nothing when no demo records are present — the common case — so a
 * real deployment carries no trace of this.
 */
export function DemoDataBadge() {
  const { data: isDemo } = useQuery({
    queryKey: ["demo-data-marker"],
    staleTime: 5 * 60_000,
    queryFn: async () => {
      // One record is enough: the seed stamps every record it writes, so the
      // first page answers the question without pulling the catalog.
      const { items } = await fetchOkhList({ page: 1, page_size: 1 });
      return items.some((item) => Boolean(item.metadata?.demo));
    },
  });

  // Either source counts: records seeded server-side (make seed-demo), or the
  // visitor's own client-side demo mode.
  if (!isDemo && !demoModeEnabled()) return null;

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-warning/30 bg-warning/10 px-2.5 py-0.5 text-xs font-medium text-warning-ink"
      title="This instance is loaded with the seeded demo dataset (make seed-demo)"
    >
      <FlaskConical aria-hidden="true" className="h-3.5 w-3.5" />
      Demo data
    </span>
  );
}
