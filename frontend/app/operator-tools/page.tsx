import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { siteConfig } from "../../src/lib/site/config";
import { OperatorToolsView } from "../../src/features/site/OperatorToolsView";

export const metadata: Metadata = { title: "Operator Tools" };

// Per-request, so notFound() below actually sets a 404 status. Prerendered,
// Next bakes the not-found boundary into a static page and serves it 200 —
// the page looks right and the status lies, which is worse than either.
export const dynamic = "force-dynamic";

export default function OperatorToolsPage() {
  // Gated here, in the server component, not in the client one: notFound()
  // after the response has begun streaming renders the boundary but cannot set
  // the status, so a disabled instance would answer 200 for a route it does
  // not have. On the default deployment this route genuinely does not exist.
  if (!siteConfig.enabled) notFound();
  return <OperatorToolsView />;
}
