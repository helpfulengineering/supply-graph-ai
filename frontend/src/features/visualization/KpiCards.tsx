import type { Kpi } from "./supplyTreeAdapter";

/** Presentational KPI grid; values come from the supply-tree adapter. */
export function KpiCards({ kpis }: { kpis: Kpi[] }) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      {kpis.map((k) => (
        <div
          key={k.label}
          className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {k.label}
          </p>
          <p className="mt-2 text-3xl font-bold tabular-nums text-slate-800 dark:text-slate-100">
            {k.value}
          </p>
        </div>
      ))}
    </div>
  );
}
