import type { HumanSummary } from "../../types/match";

interface Props {
  summary: HumanSummary;
  coverageGaps: string[];
  suggestions: string[];
  matchSummaryText: string;
  processingTime?: number;
}

export function MatchHumanSummary({
  summary,
  coverageGaps,
  suggestions,
  matchSummaryText,
  processingTime,
}: Props) {
  return (
    <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Match Summary
        </h3>
        {processingTime !== undefined && (
          <span className="text-xs text-slate-400 dark:text-slate-500 tabular-nums whitespace-nowrap">
            {processingTime.toFixed(1)}s
          </span>
        )}
      </div>

      {/* Executive summary */}
      <p className="text-base font-medium text-slate-800 dark:text-slate-100">
        {summary.executive}
      </p>

      {/* Technical summary */}
      <p className="font-mono text-xs text-slate-500 dark:text-slate-400">{matchSummaryText}</p>

      <div className="grid gap-4 sm:grid-cols-3">
        {/* Risks */}
        {summary.key_insights.risks.length > 0 && (
          <InsightBlock
            title="Risks"
            items={summary.key_insights.risks}
            iconColor="text-red-500"
            icon="⚠"
          />
        )}

        {/* Opportunities */}
        {summary.key_insights.opportunities.length > 0 && (
          <InsightBlock
            title="Opportunities"
            items={summary.key_insights.opportunities}
            iconColor="text-green-600"
            icon="✓"
          />
        )}

        {/* Recommendations */}
        {summary.key_insights.recommendations.length > 0 && (
          <InsightBlock
            title="Recommendations"
            items={summary.key_insights.recommendations}
            iconColor="text-indigo-500"
            icon="→"
          />
        )}
      </div>

      {/* Coverage gaps */}
      {coverageGaps.length > 0 && (
        <div className="rounded-lg bg-yellow-50 px-4 py-3 dark:bg-yellow-950/40">
          <p className="text-xs font-semibold text-yellow-700 dark:text-yellow-400">
            Coverage gaps: {coverageGaps.join(", ")}
          </p>
        </div>
      )}

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <ul className="space-y-1">
          {suggestions.map((s, i) => (
            <li key={i} className="text-xs text-slate-500 dark:text-slate-400">
              · {s}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function InsightBlock({
  title,
  items,
  icon,
  iconColor,
}: {
  title: string;
  items: string[];
  icon: string;
  iconColor: string;
}) {
  return (
    <div>
      <p className="mb-2 text-xs font-semibold text-slate-500 dark:text-slate-400">{title}</p>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-1.5 text-xs text-slate-600 dark:text-slate-300">
            <span className={`mt-0.5 shrink-0 ${iconColor}`} aria-hidden="true">{icon}</span>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
