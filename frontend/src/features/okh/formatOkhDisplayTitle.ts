/**
 * Display-only Title Case for OKH catalog titles.
 * Stored titles are often kebab/snake slugs; this does not mutate storage.
 */

const ACRONYMS = new Set([
  "3d",
  "3dp",
  "cad",
  "cam",
  "cnc",
  "diy",
  "gpl",
  "iso",
  "led",
  "oem",
  "pcb",
  "ppe",
  "pwm",
  "sla",
  "sls",
  "usb",
]);

function formatToken(token: string): string {
  if (!token) return token;
  const lower = token.toLowerCase();
  if (ACRONYMS.has(lower)) {
    return lower.toUpperCase();
  }
  // Preserve mixed alphanumeric tokens like "v1.0" / "8655" as-is after case normalize
  if (/^\d/.test(token) && /[a-zA-Z]/.test(token)) {
    return token.toUpperCase();
  }
  if (/^\d+$/.test(token)) {
    return token;
  }
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

/** Convert kebab/snake/spaced OKH titles into Title Case with spaces. */
export function formatOkhDisplayTitle(raw: string | null | undefined): string {
  const s = (raw ?? "").trim();
  if (!s) return "Untitled Design";

  const tokens = s.split(/[-_\s]+/).filter(Boolean);
  if (tokens.length === 0) return "Untitled Design";

  return tokens.map(formatToken).join(" ");
}
