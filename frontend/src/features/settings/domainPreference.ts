/** Browser-local OHM matching domain preference (Settings → Domain). */

export type OhmDomain = "manufacturing" | "cooking";

export const DEFAULT_DOMAIN: OhmDomain = "manufacturing";

export const STORAGE_KEY = "ohm-domain";

/** Coerce a stored/API value to a known domain; unknown → manufacturing. */
export function parseDomain(raw: string | null | undefined): OhmDomain {
  if (raw === "cooking" || raw === "manufacturing") return raw;
  return DEFAULT_DOMAIN;
}
