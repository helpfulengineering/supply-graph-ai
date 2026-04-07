import type { VisualizationData } from "../../types/supply-tree";

interface Props {
  data: VisualizationData;
}

interface CardDef {
  label: string;
  value: React.ReactNode;
  sub?: string;
  accent?: string;
}

function scoreColor(score: number): string {
  if (score >= 0.8) return "text-green-600 dark:text-green-400";
  if (score >= 0.5) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-500 dark:text-red-400";
}

export function KpiCards({ data }: Props) {
  const kpis = data.dashboard.kpis;
  const overview = data.matching.overview;
  const resourceCost = data.supply_tree.resource_cost;

  const cards: CardDef[] = [
    {
      label: "Solution Score",
      value: (
        <span className={`text-3xl font-bold tabular-nums ${scoreColor(kpis.solution_score)}`}>
          {Math.round(kpis.solution_score * 100)}%
        </span>
      ),
      sub: overview.matching_mode,
    },
    {
      label: "Facilities",
      value: <span className="text-3xl font-bold tabular-nums text-slate-800 dark:text-slate-100">{kpis.tree_count}</span>,
      sub: kpis.tree_count === 1 ? "single-level" : "multi-facility",
    },
    {
      label: "Dependencies",
      value: <span className="text-3xl font-bold tabular-nums text-slate-800 dark:text-slate-100">{kpis.edge_count}</span>,
      sub: `${kpis.stage_count} production stage${kpis.stage_count !== 1 ? "s" : ""}`,
    },
    {
      label: "Est. Cost",
      value: (
        <span className="text-3xl font-bold tabular-nums text-slate-800 dark:text-slate-100">
          {resourceCost.total_estimated_cost != null
            ? `$${resourceCost.total_estimated_cost.toLocaleString()}`
            : "—"}
        </span>
      ),
      sub: resourceCost.total_estimated_time != null
        ? `${resourceCost.total_estimated_time} days est.`
        : "Cost data unavailable",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      {cards.map(({ label, value, sub }) => (
        <div
          key={label}
          className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {label}
          </p>
          <div className="mt-2">{value}</div>
          {sub && (
            <p className="mt-1 text-xs text-slate-400 dark:text-slate-500 capitalize">{sub}</p>
          )}
        </div>
      ))}
    </div>
  );
}
