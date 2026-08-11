import type { Kpi } from "./supplyTreeAdapter";
import { PANEL } from "../../components/ui/surface";

/** Presentational KPI grid; values come from the supply-tree adapter. */
export function KpiCards({ kpis }: { kpis: Kpi[] }) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      {kpis.map((k) => (
        <div key={k.label} className={PANEL}>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {k.label}
          </p>
          <p className="mt-2 text-3xl font-bold tabular-nums text-foreground">
            {k.value}
          </p>
        </div>
      ))}
    </div>
  );
}
