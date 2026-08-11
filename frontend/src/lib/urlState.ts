/**
 * Query strings that keep what they do not own.
 *
 * Every surface that writes to the address bar used to rebuild it from its own
 * state — the network filters from the filter set, and nothing else. That is
 * fine while one thing owns the query string and wrong the moment two do: the
 * look (`theme`, `mode`) now rides in the URL on every page, and a rebuild
 * from scratch silently dropped it the first time anyone touched a filter.
 *
 * So writers merge rather than replace. A key set to null, undefined, or the
 * empty string is removed, which is how a cleared filter disappears instead of
 * lingering as `?country=`.
 */
export function mergeParams(
  base: URLSearchParams,
  updates: Record<string, string | number | null | undefined>,
): string {
  const next = new URLSearchParams(base);
  for (const [key, value] of Object.entries(updates)) {
    if (value === null || value === undefined || value === "") next.delete(key);
    else next.set(key, String(value));
  }
  return next.toString();
}

/** `?a=b` for a non-empty query string, `""` otherwise — ready to concatenate. */
export function toSearch(query: string): string {
  return query ? `?${query}` : "";
}

/**
 * A positive integer from a query parameter, or 1.
 *
 * `?page=0`, `?page=-3`, and `?page=banana` are all the first page: a bad
 * parameter in a shared link should land somewhere sensible rather than on an
 * empty results grid.
 */
export function pageFromParam(value: string | null): number {
  const n = Number(value);
  return Number.isInteger(n) && n > 0 ? n : 1;
}

/**
 * A value constrained to a known set, or the fallback.
 *
 * The same guard `filtersFromParams` applies to `source`: a query parameter is
 * whatever the sender typed, and a view mode of "banana" should not reach the
 * component that switches on it.
 */
export function oneOf<T extends string>(
  value: string | null,
  allowed: readonly T[],
  fallback: T,
): T {
  return allowed.includes(value as T) ? (value as T) : fallback;
}
