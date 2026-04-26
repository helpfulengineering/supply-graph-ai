import { Badge } from "../../components/ui/Badge";
import type { FacilityDetail, MatchSolution } from "../../types/match";

interface Props {
  solution: MatchSolution;
  isExpanded: boolean;
  onToggle: () => void;
  solutionId?: string;
  isSelected?: boolean;
  onSelect?: (id: string, checked: boolean) => void;
}

/**
 * Shows the fraction of requirements met as a bar.
 * Falls back to the raw confidence score when no requirement breakdown exists.
 * This prevents the misleading "100% — ✗ Not matched" combination that occurred
 * when `confidence` was 1.0 but no capabilities were actually matched.
 */
function RequirementsBar({
  matchedCount,
  totalReqs,
  confidence,
}: {
  matchedCount: number;
  totalReqs: number;
  confidence: number;
}) {
  const hasReqs = totalReqs > 0;
  const pct = hasReqs
    ? Math.round((matchedCount / totalReqs) * 100)
    : Math.round(confidence * 100);
  const colorClass =
    pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-yellow-500" : "bg-red-400";
  const confidencePct = Math.round(confidence * 100);

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-28 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
        <div
          className={`h-2 rounded-full ${colorClass} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex flex-col leading-none">
        <span className="text-sm font-semibold tabular-nums text-slate-700 dark:text-slate-200">
          {pct}%
        </span>
        {hasReqs && (
          <span className="text-[10px] tabular-nums text-slate-400 dark:text-slate-500">
            conf: {confidencePct}%
          </span>
        )}
      </div>
    </div>
  );
}

const rankLabel = (r: number) => {
  const suffixes = ["st", "nd", "rd"];
  return `${r}${suffixes[r - 1] ?? "th"}`;
};

/** Inline chip list for the facilities that make up a composite solution. */
function FacilityChips({ details }: { details: FacilityDetail[] }) {
  return (
    <div className="flex flex-wrap gap-1.5 mt-1">
      {details.map((d) => (
        <span
          key={d.facility_id ?? d.facility_name}
          className="inline-flex items-center rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700 ring-1 ring-inset ring-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-300 dark:ring-indigo-800"
        >
          {d.facility_name}
        </span>
      ))}
    </div>
  );
}

/** Expanded detail panel for a single facility within a composite solution. */
function CompositeFacilityPanel({ detail }: { detail: FacilityDetail }) {
  const fac = detail.facility;
  const processes = (fac.manufacturing_processes as string[] | undefined) ?? [];
  const city = (fac.location as { city?: string; country?: string } | undefined)?.city ?? "";
  const country = (fac.location as { city?: string; country?: string } | undefined)?.country ?? "";
  const locationStr = [city, country].filter(Boolean).join(", ");

  return (
    <div className="rounded-lg border border-slate-100 dark:border-slate-800 p-3 space-y-1.5">
      <p className="font-medium text-sm text-slate-700 dark:text-slate-200">
        {detail.facility_name}
      </p>
      {locationStr && (
        <p className="text-xs text-slate-400 dark:text-slate-500">{locationStr}</p>
      )}
      {processes.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {processes.slice(0, 6).map((p) => (
            <Badge key={p} variant="default">
              {p.replace("https://en.wikipedia.org/wiki/", "")}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

export function MatchResultCard({
  solution,
  isExpanded,
  onToggle,
  isSelected = false,
  onSelect,
}: Props) {
  const isComposite = Boolean(solution.is_composite);

  // ── Composite path ──────────────────────────────────────────────────────────
  const coveredCount = isComposite
    ? (solution.metrics.covered_process_count ?? 0)
    : 0;
  const requiredCount = isComposite
    ? (solution.metrics.required_process_count ?? 0)
    : 0;
  const compositeMatched = isComposite && requiredCount > 0 && coveredCount >= requiredCount;
  const facilityDetails = solution.facility_details ?? [];

  // ── Single-facility path ────────────────────────────────────────────────────
  const isMatched = isComposite
    ? compositeMatched
    : solution.explanation?.overall_status === "matched";
  const missing = isComposite ? [] : (solution.explanation?.missing_capabilities ?? []);
  const layers = solution.explanation?.matching_layers_used ?? [];
  const reqs = isComposite ? [] : (solution.explanation?.requirement_matches ?? []);
  const matchedCount = isComposite ? coveredCount : reqs.filter((r) => r.status === "matched").length;
  const totalDisplayReqs = isComposite ? requiredCount : reqs.length;

  const facility = solution.facility;
  const facilityLocation = `${facility.location.city ?? ""}, ${facility.location.country ?? ""}`.replace(/^, |, $/, "");

  return (
    <div
      className={[
        "rounded-xl border transition-shadow",
        isSelected
          ? "border-indigo-400 ring-1 ring-indigo-300 dark:border-indigo-600 dark:ring-indigo-700"
          : isExpanded
          ? "border-indigo-300 shadow-md dark:border-indigo-700"
          : "border-slate-200 hover:border-slate-300 dark:border-slate-700 dark:hover:border-slate-600",
        "bg-white dark:bg-slate-900",
      ].join(" ")}
    >
      {/* Summary row — always visible */}
      <div className="flex items-start gap-0 p-5">
        {/* Selection checkbox */}
        {onSelect && (
          <div
            className="mr-3 mt-1 shrink-0"
            onClick={(e) => e.stopPropagation()}
          >
            <input
              type="checkbox"
              checked={isSelected}
              onChange={(e) => onSelect(solution.facility_id, e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800"
              aria-label={`Select ${solution.facility_name}`}
            />
          </div>
        )}

        <button
          className="flex-1 text-left"
          onClick={onToggle}
          aria-expanded={isExpanded}
        >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          {/* Left: rank + name / facility chips */}
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-7 w-10 shrink-0 items-center justify-center rounded-md bg-slate-100 text-xs font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {rankLabel(solution.rank)}
            </span>
            <div className="min-w-0">
              {isComposite ? (
                <>
                  <p className="font-semibold text-slate-800 dark:text-slate-100">
                    Multi-step solution
                  </p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    {facilityDetails.length} facilities · combined match
                  </p>
                  {facilityDetails.length > 0 && (
                    <FacilityChips details={facilityDetails} />
                  )}
                </>
              ) : (
                <>
                  <p className="font-semibold text-slate-800 dark:text-slate-100">
                    {solution.facility_name}
                  </p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{facilityLocation}</p>
                </>
              )}
            </div>
          </div>

          {/* Right: confidence + status + chevron */}
          <div className="flex items-center gap-4 flex-wrap">
            <RequirementsBar
              matchedCount={matchedCount}
              totalReqs={totalDisplayReqs}
              confidence={solution.confidence}
            />
            <Badge variant={isMatched ? "green" : "red"}>
              {isMatched ? "✓ Matched" : "✗ Not matched"}
            </Badge>
            {!isComposite && facility.certifications && facility.certifications.length > 0 && (
              <Badge variant="default">{facility.certifications[0]}</Badge>
            )}
            <span
              className={`text-slate-400 transition-transform dark:text-slate-500 ${isExpanded ? "rotate-180" : ""}`}
              aria-hidden="true"
            >
              ▾
            </span>
          </div>
        </div>

        {/* Quick stats row */}
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
          <span>{matchedCount}/{totalDisplayReqs} requirements met</span>
          {!isComposite && layers.length > 0 && <span>Layers: {layers.join(", ")}</span>}
          {!isComposite && facility.typical_batch_size && <span>Batch: {facility.typical_batch_size}</span>}
          {!isComposite && facility.access_type && <span>{facility.access_type}</span>}
          {missing.length > 0 && (
            <span className="text-red-500 dark:text-red-400">
              Missing: {missing.join(", ")}
            </span>
          )}
        </div>
        </button>
      </div>

      {/* Expanded detail panel */}
      {isExpanded && (
        <div className="border-t border-slate-100 dark:border-slate-800 px-5 pb-6 pt-5 space-y-6">
          {isComposite ? (
            /* ── Composite expanded view ──────────────────────────────────── */
            <div className="space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Participating Facilities
              </h4>
              <p className="text-sm text-green-700 dark:text-green-400">
                ✓ Together these {facilityDetails.length} facilities cover all {requiredCount} process requirement{requiredCount !== 1 ? "s" : ""}.
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                {facilityDetails.map((d) => (
                  <CompositeFacilityPanel key={d.facility_id ?? d.facility_name} detail={d} />
                ))}
              </div>
            </div>
          ) : (
            /* ── Single-facility expanded view ────────────────────────────── */
            <div className="grid gap-6 md:grid-cols-2">
              {/* Explanation */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Match Explanation
                </h4>
                {solution.explanation?.why_matched && (
                  <p className="text-sm text-green-700 dark:text-green-400">
                    ✓ {solution.explanation.why_matched}
                  </p>
                )}
                {solution.explanation?.why_not_matched && (
                  <p className="text-sm text-red-600 dark:text-red-400">
                    ✗ {solution.explanation.why_not_matched}
                  </p>
                )}

                {/* Requirement breakdown */}
                {reqs.length > 0 && (
                  <div>
                    <p className="mb-2 text-xs font-medium text-slate-500 dark:text-slate-400">
                      Requirement breakdown
                    </p>
                    <ul className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
                      {reqs.map((r, i) => (
                        <li key={i} className="flex items-start gap-2 text-xs">
                          <span className={r.status === "matched" ? "text-green-500 mt-0.5" : "text-red-400 mt-0.5"}>
                            {r.status === "matched" ? "✓" : "✗"}
                          </span>
                          <div className="min-w-0">
                            <span className="font-medium text-slate-700 dark:text-slate-200">
                              {r.requirement_value}
                            </span>
                            {r.requirement_part_name && (
                              <span className="text-slate-400 dark:text-slate-500"> (part: {r.requirement_part_name})</span>
                            )}
                            {r.matched_capability && (
                              <span className="text-slate-500 dark:text-slate-400"> → {r.matched_capability}</span>
                            )}
                            {r.matching_layer && (
                              <span className="ml-1 text-slate-400 dark:text-slate-500">[{r.matching_layer}]</span>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Facility detail */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Facility Details
                </h4>
                <dl className="space-y-2 text-sm">
                  {facility.description && (
                    <p className="text-slate-600 dark:text-slate-300 italic">{facility.description}</p>
                  )}
                  <div className="flex gap-2">
                    <dt className="w-28 shrink-0 text-xs text-slate-400 dark:text-slate-500">Status</dt>
                    <dd className="text-slate-700 dark:text-slate-200">{facility.facility_status ?? "—"}</dd>
                  </div>
                  <div className="flex gap-2">
                    <dt className="w-28 shrink-0 text-xs text-slate-400 dark:text-slate-500">Access</dt>
                    <dd className="text-slate-700 dark:text-slate-200">{facility.access_type ?? "—"}</dd>
                  </div>
                  {facility.date_founded && (
                    <div className="flex gap-2">
                      <dt className="w-28 shrink-0 text-xs text-slate-400 dark:text-slate-500">Founded</dt>
                      <dd className="text-slate-700 dark:text-slate-200">{facility.date_founded}</dd>
                    </div>
                  )}
                  {facility.certifications && facility.certifications.length > 0 && (
                    <div className="flex gap-2">
                      <dt className="w-28 shrink-0 text-xs text-slate-400 dark:text-slate-500">Certifications</dt>
                      <dd className="flex flex-wrap gap-1">
                        {facility.certifications.map((c) => (
                          <Badge key={c} variant="blue">{c}</Badge>
                        ))}
                      </dd>
                    </div>
                  )}
                  {facility.manufacturing_processes.length > 0 && (
                    <div className="flex gap-2">
                      <dt className="w-28 shrink-0 text-xs text-slate-400 dark:text-slate-500">Processes</dt>
                      <dd className="flex flex-wrap gap-1">
                        {facility.manufacturing_processes.slice(0, 6).map((p) => (
                          <Badge key={p} variant="default">
                            {p.replace("https://en.wikipedia.org/wiki/", "")}
                          </Badge>
                        ))}
                      </dd>
                    </div>
                  )}
                  {facility.equipment && facility.equipment.length > 0 && (
                    <div className="flex gap-2">
                      <dt className="w-28 shrink-0 text-xs text-slate-400 dark:text-slate-500">Equipment</dt>
                      <dd className="text-slate-700 dark:text-slate-200">
                        {facility.equipment.length} piece{facility.equipment.length !== 1 ? "s" : ""}
                      </dd>
                    </div>
                  )}
                </dl>
              </div>
            </div>
          )}

          {/* Human-readable explanation verbatim (single-facility only) */}
          {!isComposite && solution.explanation_human && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Full Explanation
              </p>
              <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {solution.explanation_human}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
