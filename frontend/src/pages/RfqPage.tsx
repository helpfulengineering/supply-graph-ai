import { useLocation } from "react-router-dom";
import { RfqView } from "../features/rfq/RfqView";
import type { RfqNavigationState } from "../types/rfq";

export function RfqPage() {
  const location = useLocation();
  const navState = (location.state as RfqNavigationState) ?? null;
  return <RfqView navState={navState} />;
}
