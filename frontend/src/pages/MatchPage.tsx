import { useSearchParams } from "react-router-dom";
import { MatchView } from "../features/match/MatchView";

export function MatchPage() {
  const [searchParams] = useSearchParams();
  const okhId = searchParams.get("okh_id") ?? undefined;
  const autoRun = searchParams.get("autorun") === "1";
  // Remount when switching designs so match session state and autorun latch reset cleanly.
  return <MatchView key={okhId ?? "__none__"} okhId={okhId} autoRun={autoRun} />;
}
