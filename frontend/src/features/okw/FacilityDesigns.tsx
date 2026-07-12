import { useNavigate } from "react-router-dom";
import { Button } from "../../components/ui/button";

/**
 * Hand-off from a facility detail into Match a Design with this facility
 * pre-selected. Matching is intentional: the user picks a design and runs it.
 */
export function FacilityDesigns({ okwId }: { okwId: string }) {
  const navigate = useNavigate();
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        Matching designs
      </h2>
      <p className="mb-4 text-sm text-slate-600 dark:text-slate-300">
        Find which catalog designs this facility can produce. You’ll pick a design
        and confirm facility filters on the Match page before anything runs.
      </p>
      <Button onClick={() => navigate(`/match?okw_id=${encodeURIComponent(okwId)}`)}>
        Find matching designs →
      </Button>
    </section>
  );
}
