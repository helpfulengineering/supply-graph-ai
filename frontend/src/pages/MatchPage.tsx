import { useSearchParams } from "react-router-dom";
import { MatchView } from "../features/match/MatchView";

const NETWORK_AXES = ["country", "city", "process", "source", "status", "region", "access_type"] as const;

export function MatchPage() {
  const [searchParams] = useSearchParams();
  const okhId = searchParams.get("okh_id") ?? undefined;
  const autoRun = searchParams.get("autorun") === "1";

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

  // Remount when switching designs/scope so match session state and the autorun
  // latch reset cleanly.
  const key = `${okhId ?? "__none__"}:${networkFilter ? searchParams.toString() : ""}`;
  return <MatchView key={key} okhId={okhId} autoRun={autoRun} networkFilter={networkFilter} />;
}
