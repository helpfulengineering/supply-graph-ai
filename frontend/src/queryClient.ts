/**
 * Shared React Query client + localStorage persistence.
 *
 * Designs and facilities are low-volatility datasets that are expensive to
 * fetch (the unfiltered network payload is thousands of rows). We cache them
 * aggressively: a 1h stale window, no background refetch on focus/reconnect,
 * and a localStorage-backed cache so a page refresh serves instantly instead of
 * refetching everything. A manual "Refresh data" control (see NavBar) is the
 * escape hatch for pulling the latest data on demand.
 */
import { QueryClient } from "@tanstack/react-query";
import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister";
import {
  removeOldestQuery,
  type PersistQueryClientOptions,
} from "@tanstack/react-query-persist-client";

const ONE_HOUR = 60 * 60 * 1000;

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Serve cached data for an hour before considering it stale.
      staleTime: ONE_HOUR,
      // Keep unobserved data in memory longer than the persisted maxAge so
      // hydrated entries are not immediately garbage-collected.
      gcTime: 2 * ONE_HOUR,
      retry: 1,
      // Auto-refetch is off; the manual refresh control is the way to get
      // fresh data. This keeps navigation and window focus snappy.
      refetchOnWindowFocus: false,
      refetchOnReconnect: false,
    },
  },
});

/**
 * Cache buster. Bump when the persisted query shapes change (e.g. after an API
 * schema change) so stale localStorage payloads are discarded on next load.
 */
const CACHE_BUSTER = "ohm-cache-v1";

const persister = createSyncStoragePersister({
  storage: typeof window !== "undefined" ? window.localStorage : undefined,
  key: "ohm-query-cache",
  throttleTime: 1000,
  // The unfiltered facilities payload is large; if localStorage is full, drop
  // the oldest query and retry rather than failing to persist entirely.
  retry: removeOldestQuery,
});

export const persistOptions: Omit<PersistQueryClientOptions, "queryClient"> = {
  persister,
  maxAge: ONE_HOUR,
  buster: CACHE_BUSTER,
  dehydrateOptions: {
    // Only persist successful queries — never cache errors or pending states.
    shouldDehydrateQuery: (query) => query.state.status === "success",
  },
};

/**
 * Query-key prefixes for low-volatility datasets that the manual "Refresh data"
 * control should reload. Uses prefix matching, so `["network"]` covers both the
 * shared baseline list and any filtered variants.
 */
export const LOW_VOLATILITY_QUERY_KEYS = [
  ["okh-list"],
  ["network"],
  ["package-list"],
  ["domains"],
] as const;

/** Invalidate (and trigger refetch of) the low-volatility datasets. */
export async function refreshLowVolatilityData(
  client: QueryClient = queryClient,
): Promise<void> {
  await Promise.all(
    LOW_VOLATILITY_QUERY_KEYS.map((key) =>
      client.invalidateQueries({ queryKey: [...key] }),
    ),
  );
}
