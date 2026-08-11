import { useLocation, useSearchParams } from "react-router-dom";
import { MatchView } from "../features/match/MatchView";
import { CookingMatchView } from "../features/match/CookingMatchView";
import { useDomain } from "../context/DomainContext";

/** Hand-off payload from generate-from-URL: a reviewed but unsaved manifest. */
export interface InlineMatchState {
  okhManifest?: Record<string, unknown>;
  okhTitle?: string;
}

const NETWORK_AXES = ["country", "city", "process", "source", "status", "region", "access_type"] as const;

export function MatchPage() {
  const { domain } = useDomain();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  if (domain === "cooking") return <CookingMatchView />;
  const okhId = searchParams.get("okh_id") ?? undefined;
  const okwId = searchParams.get("okw_id") ?? undefined;

  // A generated design is handed over in navigation state rather than the URL:
  // it is a whole manifest, and it is deliberately not persisted anywhere.
  const inline = (location.state as InlineMatchState | null) ?? null;

  // A `network` marker (from the network surface's "Match against these" action)
  // carries the active filters into the match as a network_filter.
  let networkFilter: Record<string, string | boolean> | undefined;
  if (searchParams.get("network")) {
    networkFilter = {};
    for (const axis of NETWORK_AXES) {
      const value = searchParams.get(axis);
      if (value) networkFilter[axis] = value;
    }
    networkFilter.include_mom = searchParams.get("source") !== "local";
  }

  // Remount when switching design/facility/scope so selection state resets cleanly.
  const key = `${okhId ?? "__none__"}:${okwId ?? ""}:${networkFilter ? searchParams.toString() : ""}:${inline?.okhManifest ? "inline" : ""}`;
  return (
    <MatchView
      key={key}
      okhId={okhId}
      okwId={okwId}
      networkFilter={networkFilter}
      inlineManifest={inline?.okhManifest}
      inlineTitle={inline?.okhTitle}
    />
  );
}
