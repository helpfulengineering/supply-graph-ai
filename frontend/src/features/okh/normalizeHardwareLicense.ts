/**
 * Collapse near-identical SPDX hardware licenses for catalog facets/display.
 *
 * Examples:
 * - CERN-OHL-P-2.0 / CERN-OHL-S-2.0 / CERN-OHL-W-2.0 → CERN-OHL-2.0
 * - AGPL-3.0-only / AGPL-3.0-or-later → AGPL-3.0
 */

export function normalizeHardwareLicense(
  raw: string | null | undefined,
): string | null {
  if (raw == null) return null;
  let s = raw.trim();
  if (!s) return null;

  // SPDX "only" / "or-later" variants → base id
  s = s.replace(/-or-later$/i, "").replace(/-only$/i, "");

  // CERN OHL family: CERN-OHL-{P|S|W}-2.0 → CERN-OHL-2.0
  const cern = s.match(/^CERN-OHL-[PSW]-(\d+(?:\.\d+)*)$/i);
  if (cern) {
    return `CERN-OHL-${cern[1]}`;
  }

  // Older CERN-OHL-1.2 style without variant letter — keep as-is after suffix strip
  return s;
}
