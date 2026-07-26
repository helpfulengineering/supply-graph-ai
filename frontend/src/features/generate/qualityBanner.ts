/**
 * Quality-report presentation mapper (pure, unit-tested).
 *
 * The banner WARNS and never blocks. Generation is heuristic-only in
 * production, so an imperfect manifest is the expected outcome, not an error —
 * the human review step is what compensates. The only hard gate is that the six
 * required OKH fields are valid before saving (see manifestTiers.ts).
 */

import type { OkhQualityReport } from "../../api/ohm/okh";

export type BannerTone = "good" | "warn" | "info";

export interface QualityBanner {
  tone: BannerTone;
  headline: string;
  missingRequired: string[];
  recommendations: string[];
}

/** Human label for whatever the backend put in `overall_quality`. */
export function qualityLabel(value: OkhQualityReport["overall_quality"]): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") {
    // Reported as a fraction in some paths, a percentage in others.
    const pct = value <= 1 ? Math.round(value * 100) : Math.round(value);
    return `${pct}%`;
  }
  const text = String(value).trim();
  return text ? text.replace(/_/g, " ") : null;
}

export function toQualityBanner(report: OkhQualityReport | null): QualityBanner {
  const missingRequired = (report?.missing_required_fields ?? []).filter(Boolean);
  const recommendations = (report?.recommendations ?? []).filter(Boolean);

  if (!report) {
    return {
      tone: "info",
      headline: "No quality report was returned for this extraction.",
      missingRequired: [],
      recommendations: [],
    };
  }

  if (missingRequired.length > 0) {
    const n = missingRequired.length;
    return {
      tone: "warn",
      headline: `${n} required field${n === 1 ? "" : "s"} could not be extracted — fill ${
        n === 1 ? "it" : "them"
      } in below.`,
      missingRequired,
      recommendations,
    };
  }

  const label = qualityLabel(report.overall_quality);
  return {
    tone: "good",
    headline: label
      ? `All required fields were extracted. Overall quality: ${label}.`
      : "All required fields were extracted.",
    missingRequired: [],
    recommendations,
  };
}
