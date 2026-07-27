/**
 * City-name normalisation for filter options (pure, unit-tested).
 *
 * Facility records carry whatever a space typed, so the city field holds a
 * minority of postal codes, street addresses, and punctuation artifacts
 * alongside real names. Left alone they fill the filter with entries like
 * "-- .", "134 Avenue du Général Leclerc", and three separate Viennas
 * ("1050 Wien", "1070 Wien", "1220 Wien").
 *
 * The rules are deliberately conservative, because most of what *looks*
 * malformed is not:
 *
 *   's-Hertogenbosch      leading apostrophe is part of the name
 *   Halle (Saale)         parenthesised qualifier is the actual name
 *   Biel/Bienne           bilingual name, not a separator
 *   Schwedt/Oder          likewise
 *   Kempten (Allgäu)      likewise
 *   ST BENOIT DE CARMAUX  "ST" is Saint, not Street
 *
 * Dropping a real city hides real facilities, which is worse than showing one
 * odd entry. So this only fixes the unambiguous cases and leaves the rest.
 *
 * Safe to normalise for filtering because the API matches city as a
 * case-insensitive SUBSTRING — sending "Wien" still matches "1050 Wien".
 */

/** Street words that indicate an address ONLY when digits are present too. */
const STREET_WORDS =
  /\b(street|str|straße|strasse|avenue|ave|road|rd|lane|weg|třída|vej|place)\b\.?/i;

/**
 * Normalise one raw city value.
 *
 * Returns null when the value is not a usable city name, so callers drop it
 * rather than showing it as an option.
 */
export function normalizeCityName(raw: string | null | undefined): string | null {
  let s = (raw ?? "").trim();
  if (!s) return null;

  // No letters at all: "-", "--", "-- .", "107-0052" (a bare postal code).
  if (!/\p{L}/u.test(s)) return null;

  // Whole value wrapped in parentheses: "(Incheon)" -> "Incheon".
  // Deliberately not applied to "Halle (Saale)", where the parens are internal.
  const wrapped = s.match(/^\((.+)\)$/);
  if (wrapped) s = wrapped[1].trim();

  // A leading slash is an artifact ("/Stavropol'"); an internal one is a real
  // bilingual name ("Biel/Bienne"), so only the leading case is stripped.
  s = s.replace(/^\/+/, "").trim();

  // Address-like: a street word AND a number. Either alone is too common in
  // legitimate names to act on ("ST BENOIT DE CARMAUX" is Saint; "Neckarauer
  // Straße 106-116" is an address).
  //
  // Checked BEFORE the postal-code strip: "134 Avenue du Général Leclerc" would
  // otherwise lose its house number first and survive as a street name.
  if (STREET_WORDS.test(s) && /\d/.test(s)) return null;

  // Leading postal code: "1050 Wien", "114 28 Stockholm", "212 18 Malmö".
  // Requires 3+ digits so house numbers ("7 Place …") are not mistaken for one.
  s = s.replace(/^\d{3,5}(\s+\d{2})?\s+/, "").trim();

  // Re-check: stripping may have left nothing usable.
  if (!/\p{L}/u.test(s)) return null;

  return s;
}

/**
 * Distinct, sorted, normalised city names.
 *
 * Values that normalise to the same name collapse, which is what merges the
 * three Viennas into one option.
 */
export function normalizedCityOptions(
  raws: (string | null | undefined)[],
): string[] {
  const seen = new Map<string, string>();
  for (const raw of raws) {
    const name = normalizeCityName(raw);
    if (!name) continue;
    const key = name.toLowerCase();
    if (!seen.has(key)) seen.set(key, name);
  }
  return [...seen.values()].sort((a, b) => a.localeCompare(b));
}
