import type { RunMatchParams } from "../../api/ohm/match";

/**
 * Match-request builder (pure, unit-tested) — module 4.
 *
 * Maps a System Mode preset to concrete match-request params. The API has no
 * single "mode" field; a mode is expressed via quality_level + strict_mode
 * (relaxed → strict). Mirrors the roadmap's minimal/standard/strict presets.
 */

export type SystemMode = "minimal" | "standard" | "strict";

export interface SystemModeInfo {
  mode: SystemMode;
  label: string;
  description: string;
}

export const SYSTEM_MODES: SystemModeInfo[] = [
  {
    mode: "minimal",
    label: "Minimal",
    description:
      "Coverage + dependency checks only, relaxed thresholds. Fastest — for crisis or low-data contexts where a partial answer now beats a perfect one later.",
  },
  {
    mode: "standard",
    label: "Standard",
    description: "Adds quality and completeness checks. The default balance.",
  },
  {
    mode: "strict",
    label: "Strict",
    description:
      "All validations and thresholds enforced. Highest confidence, slowest — for production commitments.",
  },
];

const MODE_PARAMS: Record<SystemMode, { qualityLevel: string; strictMode: boolean }> = {
  minimal: { qualityLevel: "hobby", strictMode: false },
  standard: { qualityLevel: "professional", strictMode: false },
  strict: { qualityLevel: "medical", strictMode: true },
};

export function buildMatchRequest(
  okhId: string,
  mode: SystemMode,
  maxResults?: number,
  okwIds?: string[],
  networkFilter?: Record<string, string | boolean>,
): RunMatchParams {
  const subset = okwIds && okwIds.length > 0 ? { okwIds } : {};
  // Network filter (local ∪ MoM) can combine with an explicit id subset so the
  // Match page can pick individual MoM/local spaces from the network list.
  if (networkFilter) {
    return { okhId, ...MODE_PARAMS[mode], maxResults, networkFilter, ...subset };
  }
  return { okhId, ...MODE_PARAMS[mode], maxResults, ...subset };
}
