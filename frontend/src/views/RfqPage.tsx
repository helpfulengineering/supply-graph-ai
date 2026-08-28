"use client";

import { useSearchParams } from "next/navigation";
import { RfqView } from "../features/rfq/RfqView";
import { readNavState } from "../lib/navState";
import type { RfqNavigationState } from "../types/rfq";

export function RfqPage() {
  const searchParams = useSearchParams();
  const navState = readNavState<RfqNavigationState>(searchParams.get("h"));
  return <RfqView navState={navState} />;
}
