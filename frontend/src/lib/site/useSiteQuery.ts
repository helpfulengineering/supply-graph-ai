"use client";

import { useCallback, useEffect, useState } from "react";
import type { Result } from "./stack";

/**
 * The read half of every Operator Tools panel: run a `Result`-returning call,
 * expose loading / data / error, and offer a reload for after a mutation.
 *
 * DELIBERATELY NOT REACT QUERY, though the app uses it everywhere else. The
 * app's client is wrapped in a persister (see the providers) that writes query
 * results to storage so a reload starts warm. That is right for the design and
 * facility catalogues and wrong for this data: these panels read visitor names,
 * email addresses, and the pages people visited, and an operator's unmasked
 * read would be spooled onto the device to be found later by anyone who opens
 * the browser. sessionStorage-only for the token and nothing at rest for what
 * it unlocks is the whole point of the tier — a cache would quietly undo it.
 *
 * So this stays deliberately small: no cache, no dedupe, no background
 * refetch. A panel that is not mounted is a panel holding no PII.
 */
export interface SiteQuery<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

/**
 * @param run    the call, or null when the tier cannot make it yet (no visitor,
 *               no token) — a null `run` settles to empty rather than erroring,
 *               because "you are not signed in" is a state the panel renders
 *               itself, not a failure.
 * @param deps   re-run when these change, alongside `reload()`.
 */
export function useSiteQuery<T>(
  run: (() => Promise<Result<T>>) | null,
  deps: readonly unknown[],
): SiteQuery<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [reads, setReads] = useState(0);

  useEffect(() => {
    if (!run) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    void run().then((result) => {
      // An unmounted panel must not land its rows in state — that is the
      // React warning, but it is also the PII rule above: nothing survives
      // the panel that read it.
      if (cancelled) return;
      setLoading(false);
      if (result.ok) {
        setData(result.data);
        setError(null);
      } else {
        setData(null);
        setError(result.error);
      }
    });
    return () => {
      cancelled = true;
    };
    // `run` is rebuilt every render by callers that close over props, so the
    // caller's own deps are the honest dependency list.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, reads]);

  const reload = useCallback(() => setReads((n) => n + 1), []);

  return { data, error, loading, reload };
}
