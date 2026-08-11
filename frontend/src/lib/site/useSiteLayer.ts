"use client";

import { useEffect, useState } from "react";
import { siteConfig } from "./config";
import { isOperator, track, visitor, type Visitor } from "./stack";

export interface SiteLayerState {
  /** Whether this instance opted into the site layer at all. */
  enabled: boolean;
  /** The signed-in visitor, if the gate has been completed on this device. */
  visitor: Visitor | null;
  /**
   * Site-layer operator. Never conflate with useAuth().isAdmin, which is
   * application authorization from the backend's whoami.
   */
  isOperator: boolean;
}

/**
 * Reads site-layer state without ever blocking a render.
 *
 * When the layer is disabled every field is its empty value and no network
 * call is made — the caller's `enabled === false` branch should render nothing
 * at all rather than an explanation, because off is the default deployment,
 * not a misconfiguration.
 */
export function useSiteLayer(): SiteLayerState {
  const [state, setState] = useState<SiteLayerState>({
    enabled: siteConfig.enabled,
    visitor: null,
    isOperator: false,
  });

  useEffect(() => {
    if (!siteConfig.enabled) return;
    let cancelled = false;

    setState((s) => ({ ...s, visitor: visitor() }));
    void isOperator().then((op) => {
      if (!cancelled) setState((s) => ({ ...s, isOperator: op }));
    });
    track("page_view", { path: window.location.pathname });

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
