/**
 * Site-layer configuration — the optional capability switch.
 *
 * OHM is software you run yourself; the hosted instance is a convenience, not
 * the product. So the whole site layer (visitor gate, telemetry, whitelabel,
 * Mission Control) is a per-instance optionality that defaults to OFF, in the
 * same idiom as OHM_SECURITY_MODE: a posture selected by environment variable,
 * read through config, never hard-coded.
 *
 * OFF IS A FIRST-CLASS STATE, NOT A FALLBACK. With no Supabase configured the
 * instance is not degraded — that is the default, fully supported deployment.
 * Nothing here may render "configure Supabase" as an error or an empty panel;
 * surfaces simply do not exist, and theme/mode preferences stay on the device.
 *
 * The two env vars are NEXT_PUBLIC_ because the anon key is public by design:
 * it can only reach whitelisted SECURITY DEFINER RPCs (see supabase/schema.sql).
 * Privileged operations need the operator token, which never leaves
 * sessionStorage and is verified server-side.
 */

const url = process.env.NEXT_PUBLIC_OHM_SUPABASE_URL ?? "";
const anonKey = process.env.NEXT_PUBLIC_OHM_SUPABASE_ANON_KEY ?? "";

/** Placeholder guard, matching the reference: an unsubstituted %VAR% is unset. */
function unset(v: string): boolean {
  return !v || v.startsWith("%");
}

export interface SiteConfig {
  enabled: boolean;
  url: string;
  anonKey: string;
}

export const siteConfig: SiteConfig = {
  enabled: !unset(url) && !unset(anonKey),
  url: unset(url) ? "" : url,
  anonKey: unset(anonKey) ? "" : anonKey,
};

/** True when this instance opted into the site layer. */
export function siteLayerEnabled(): boolean {
  return siteConfig.enabled;
}
