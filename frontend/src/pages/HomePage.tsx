import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchDomains, fetchMetrics } from "../api/ohm/utility";
import { listSolutions } from "../api/ohm/supply-tree";
import { Badge } from "../components/ui/Badge";

const JOURNEYS = [
  { to: "/okh", icon: "🔩", title: "Designs", desc: "Browse open hardware designs by category and capability." },
  { to: "/facilities", icon: "🏭", title: "Facilities", desc: "Explore manufacturing facilities and their capabilities." },
  { to: "/match", icon: "⚡", title: "Match", desc: "Find facilities that can produce a design." },
  { to: "/solutions", icon: "🌳", title: "Solutions", desc: "Revisit saved supply-tree solutions." },
];

export function HomePage() {
  const domains = useQuery({ queryKey: ["domains"], queryFn: fetchDomains, staleTime: 300_000 });
  const metrics = useQuery({ queryKey: ["metrics"], queryFn: fetchMetrics, staleTime: 60_000 });
  const solutions = useQuery({ queryKey: ["solutions"], queryFn: listSolutions, staleTime: 30_000 });

  const recent = (solutions.data ?? []).slice(0, 3);
  const online = !domains.isError && !metrics.isError;

  return (
    <div className="space-y-10 py-4">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Open Hardware Manager</h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          Match open hardware designs to manufacturing facilities and explore the resulting supply
          chains.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {JOURNEYS.map((j) => (
          <Link
            key={j.to}
            to={j.to}
            className="group flex flex-col gap-2 rounded-xl border border-slate-200 bg-white p-5 no-underline shadow-sm transition-shadow hover:shadow-md dark:border-slate-700 dark:bg-slate-900"
          >
            <span className="text-3xl" aria-hidden="true">{j.icon}</span>
            <p className="font-semibold text-slate-800 group-hover:text-indigo-600 dark:text-slate-100 dark:group-hover:text-indigo-400">
              {j.title}
            </p>
            <p className="text-sm text-muted-foreground">{j.desc}</p>
          </Link>
        ))}
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-foreground">Recent solutions</h2>
            <Link to="/solutions" className="text-sm text-indigo-600 hover:underline dark:text-indigo-400">
              View all →
            </Link>
          </div>
          {recent.length === 0 ? (
            <p className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
              No saved solutions yet — run a match to create one.
            </p>
          ) : (
            <ul className="space-y-2">
              {recent.map((s) => (
                <li key={s.id}>
                  <Link
                    to={`/visualization/${s.id}`}
                    className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4 no-underline hover:bg-accent dark:border-slate-700 dark:bg-slate-900"
                  >
                    <span className="text-sm font-medium text-slate-800 dark:text-slate-100">
                      {s.okh_title || (s.okh_id ? `${s.okh_id.slice(0, 8)}…` : "Untitled")}
                    </span>
                    <Badge variant={s.score >= 0.8 ? "green" : s.score >= 0.5 ? "yellow" : "red"}>
                      {Math.round(s.score * 100)}%
                    </Badge>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">System</h2>
          <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center gap-2">
              <span
                className={`h-2.5 w-2.5 rounded-full ${online ? "bg-green-500" : "bg-red-500"}`}
                aria-hidden="true"
              />
              <span className="text-sm text-slate-700 dark:text-slate-200">
                {online ? "API online" : "API unreachable"}
              </span>
            </div>
            {metrics.data && (
              <p className="text-xs text-muted-foreground">
                {metrics.data.total_errors} error{metrics.data.total_errors !== 1 ? "s" : ""} ·{" "}
                {metrics.data.recent_requests_1h} requests (1h)
              </p>
            )}
            <div>
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Domains
              </p>
              <div className="flex flex-wrap gap-1.5">
                {(domains.data ?? []).map((d) => (
                  <Badge key={d.id} variant="blue">{d.name}</Badge>
                ))}
                {domains.isLoading && (
                  <span className="text-xs text-muted-foreground">loading…</span>
                )}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
