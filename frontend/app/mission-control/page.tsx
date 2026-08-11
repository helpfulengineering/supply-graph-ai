import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { siteConfig } from "../../src/lib/site/config";
import { MissionControl } from "../../src/features/site/MissionControl";

export const metadata: Metadata = { title: "Mission Control" };

// Per-request, so notFound() below actually sets a 404 status. Prerendered,
// Next bakes the not-found boundary into a static page and serves it 200 —
// the page looks right and the status lies, which is worse than either.
export const dynamic = "force-dynamic";

export default function MissionControlPage() {
  // Gated here, in the server component, not in the client one: notFound()
  // after the response has begun streaming renders the boundary but cannot set
  // the status, so a disabled instance would answer 200 for a route it does
  // not have. On the default deployment this route genuinely does not exist.
  if (!siteConfig.enabled) notFound();
  return <MissionControl />;
}
