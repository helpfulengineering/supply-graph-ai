/**
 * Near-miss tolerance (pure, unit-tested).
 *
 * The match API returns facilities that do NOT satisfy every requirement
 * alongside those that do, and the UI showed both with a confidence badge — so
 * a workshop that cannot build your design appeared as "Medium · 67%". The
 * percentage is the problem: it invites people to read 67% as "probably fine",
 * and it is not comparable across designs. A design with 2 requirements drops
 * to 50% for one gap; a design with 6 drops to 83% for the same gap.
 *
 * So tolerance is expressed in MISSING REQUIREMENTS, which is both actionable
 * ("missing soldering") and stable across designs.
 *
 * The bounds are a function of the design's requirement count `r`:
 *
 *   ceiling  = max(r - 2, 0)   a facility must always satisfy at least 2
 *                              requirements, so results never degrade into
 *                              "this workshop shares one process with you"
 *   default  = min(1, ceiling) missing at most one — an easy gap to fill, and
 *                              the case worth surfacing unprompted
 */

export interface RequirementStats {
  /** Requirements the design states. */
  total: number;
  /** How many this facility does not satisfy. */
  missing: number;
}

interface RequirementMatch {
  status?: string | null;
  requirement_value?: string | null;
}

interface ExplanationLike {
  requirement_matches?: RequirementMatch[] | null;
  missing_capabilities?: unknown[] | null;
  overall_status?: string | null;
}

/**
 * Read requirement counts out of a structured explanation, counting each
 * requirement ONCE.
 *
 * The API extracts the same process twice when a design declares it in both
 * `manufacturing_processes` and `manufacturing_specs.process_requirements`, so
 * a three-requirement design reported six. A duplicate counts as matched only
 * if every copy did, so deduping cannot hide a gap.
 *
 * Returns null when the API sent no explanation — callers must not infer
 * "nothing missing" from missing data, which would resurrect the original bug
 * in a quieter form.
 */
export function requirementStats(
  explanation: ExplanationLike | null | undefined,
): RequirementStats | null {
  const matches = explanation?.requirement_matches;
  if (!Array.isArray(matches) || matches.length === 0) return null;

  const satisfied = new Map<string, boolean>();
  matches.forEach((m, i) => {
    // Fall back to the index when the value is absent, so an unlabelled
    // requirement stays its own entry rather than collapsing with others.
    const key = m?.requirement_value?.trim().toLowerCase() || `#${i}`;
    const ok = m?.status === "matched";
    satisfied.set(key, (satisfied.get(key) ?? true) && ok);
  });

  const missing = [...satisfied.values()].filter((ok) => !ok).length;
  return { total: satisfied.size, missing };
}

/** Most missing requirements a user may choose to tolerate, given `r`. */
export function toleranceCeiling(totalRequirements: number): number {
  return Math.max(totalRequirements - 2, 0);
}

/** Where the control starts: one gap, unless the design is too small to allow it. */
export function defaultTolerance(totalRequirements: number): number {
  return Math.min(1, toleranceCeiling(totalRequirements));
}

export function withinTolerance(
  stats: RequirementStats | null,
  tolerance: number,
): boolean {
  // Unknown coverage is shown rather than hidden: silently dropping results
  // because the API omitted an explanation would be worse than showing them.
  if (!stats) return true;
  return stats.missing <= tolerance;
}

/** Short, honest label for a result — never a bare percentage. */
export function coverageLabel(stats: RequirementStats | null): string {
  if (!stats) return "Coverage unknown";
  if (stats.missing === 0) return "Meets every requirement";
  return `Missing ${stats.missing} of ${stats.total} requirements`;
}
