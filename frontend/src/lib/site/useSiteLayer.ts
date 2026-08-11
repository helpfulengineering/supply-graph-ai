"use client";

import { useCallback, useEffect, useState } from "react";
import { siteConfig } from "./config";
import {
  adminStats,
  clearOperatorToken,
  isOperator,
  setOperatorToken,
  track,
  visitor,
  type Visitor,
} from "./stack";

export interface SiteLayerState {
  /** Whether this instance opted into the site layer at all. */
  enabled: boolean;
  /**
   * Whether the device's state has been read yet. False on the server and on
   * the first client render, because the visitor record lives in localStorage
   * and cannot be known during SSR.
   *
   * Callers that render something *because* nobody is signed in — the gate —
   * must wait for this, or a returning visitor gets a dialog flashed at them
   * between hydration and the first read.
   */
  ready: boolean;
  /** The signed-in visitor, if the gate has been completed on this device. */
  visitor: Visitor | null;
  /**
   * Site-layer operator. Never conflate with useAuth().isAdmin, which is
   * application authorization from the backend's whoami.
   */
  isOperator: boolean;
  /**
   * Verifies a token server-side and, if it holds, keeps it for this tab.
   * Resolves to the failure message so the form can render it, or null on
   * success. A rejected token is not stored.
   */
  unlock: (token: string) => Promise<string | null>;
  /** Forgets the operator token. Leaves the visitor record alone. */
  lock: () => void;
  /** Re-read after a sign-in or sign-out. Does not re-count the page view. */
  refresh: () => void;
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
  const [state, setState] = useState<Omit<SiteLayerState, "refresh" | "unlock" | "lock">>({
    enabled: siteConfig.enabled,
    // Nothing to wait for with the layer off: every field is already final.
    ready: !siteConfig.enabled,
    visitor: null,
    isOperator: false,
  });
  const [reads, setReads] = useState(0);

  // Telemetry is per mount, not per read: signing in at the gate refreshes the
  // state below, and a second page_view for the same visit would be a lie.
  useEffect(() => {
    if (!siteConfig.enabled) return;
    track("page_view", { path: window.location.pathname });
  }, []);

  useEffect(() => {
    if (!siteConfig.enabled) return;
    let cancelled = false;

    setState((s) => ({ ...s, ready: true, visitor: visitor() }));
    void isOperator().then((op) => {
      if (!cancelled) setState((s) => ({ ...s, isOperator: op }));
    });

    return () => {
      cancelled = true;
    };
  }, [reads]);

  const refresh = useCallback(() => setReads((n) => n + 1), []);

  // Stores only after the server accepts it, so a mistyped token never leaves
  // the tab believing it is unlocked — and never leaves a bad secret sitting
  // in sessionStorage for the next call to retry with.
  const unlock = useCallback(async (token: string): Promise<string | null> => {
    const trimmed = token.trim();
    if (!trimmed) return "Enter the operator token.";
    const probe = await adminStats(trimmed);
    if (!probe.ok) return probe.error;
    setOperatorToken(trimmed);
    setState((s) => ({ ...s, isOperator: true }));
    return null;
  }, []);

  const lock = useCallback(() => {
    clearOperatorToken();
    setState((s) => ({ ...s, isOperator: false }));
  }, []);

  return { ...state, unlock, lock, refresh };
}
