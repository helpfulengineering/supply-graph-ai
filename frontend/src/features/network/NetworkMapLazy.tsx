"use client";

import dynamic from "next/dynamic";
import { LoadingState } from "../../components/ui/states";

/**
 * Leaflet touches `window` at module evaluation, so the real NetworkMap can
 * only ever load in the browser. Every consumer imports this boundary instead
 * of NetworkMap directly.
 */
export const NetworkMap = dynamic(
  () => import("./NetworkMap").then((m) => ({ default: m.NetworkMap })),
  { ssr: false, loading: () => <LoadingState message="Loading map…" /> },
);
