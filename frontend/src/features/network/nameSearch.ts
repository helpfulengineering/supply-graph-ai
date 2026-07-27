/**
 * Name search over the loaded network spaces (pure, unit-tested).
 *
 * Client-side deliberately. The map already holds every space in memory — it
 * has to, to draw them — so filtering by name is instant and needs no round
 * trip and no backend change. `/api/okw/spaces` has no name parameter today;
 * adding one becomes worthwhile if the network outgrows what the map can hold,
 * at which point this function is the thing to replace.
 *
 * Matching is deliberately forgiving: people search for "fablab lyon" when the
 * record says "FabLab Lyon — Association", and a search that fails on word
 * order or punctuation is worse than none, because the primary call to action
 * on the site is "find your workshop".
 */

export interface NameSearchable {
  name: string;
  city?: string | null;
  country?: string | null;
}

/** Strip accents, punctuation, and case so "Coh@bit" matches "cohabit". */
export function normalizeForSearch(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/**
 * Every whitespace-separated term must appear somewhere in the haystack, in any
 * order. Substring rather than whole-word so "fab" finds "FabLab".
 */
export function matchesName<T extends NameSearchable>(space: T, query: string): boolean {
  const q = normalizeForSearch(query);
  if (!q) return true;
  // City and country are included so "lyon" finds a space whose name omits it.
  const haystack = normalizeForSearch(
    [space.name, space.city ?? "", space.country ?? ""].join(" "),
  );
  return q.split(" ").every((term) => haystack.includes(term));
}

export function filterByName<T extends NameSearchable>(spaces: T[], query: string): T[] {
  if (!normalizeForSearch(query)) return spaces;
  return spaces.filter((s) => matchesName(s, query));
}
