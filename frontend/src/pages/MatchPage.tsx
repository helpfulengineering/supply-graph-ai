import { useSearchParams } from "react-router-dom";
import { MatchView } from "../features/match/MatchView";

export function MatchPage() {
  const [searchParams] = useSearchParams();
  const okhId = searchParams.get("okh_id") ?? undefined;
  const autoRun = searchParams.get("autorun") === "1";
  return <MatchView okhId={okhId} autoRun={autoRun} />;
}
