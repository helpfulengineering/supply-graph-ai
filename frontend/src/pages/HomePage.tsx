import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchDomains, fetchMetrics } from "../api/ohm/utility";
import { fetchNetworkSpaces } from "../api/ohm/network";
import { listSolutions } from "../api/ohm/supply-tree";
import { Badge } from "../components/ui/Badge";
import { LoadingState, ErrorState } from "../components/ui/states";
import { NetworkMap } from "../features/network/NetworkMap";
import { GettingStarted } from "../features/dashboard/GettingStarted";
import { buildNetworkSummary, SOURCE_STYLES } from "../features/network/networkSummary";

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">{value}</p>
      <p className="mt-0.5 text-xs font-medium uppercase tracking-wide text-slate-600 dark:text-slate-400">
        {label}
      </p>
    </div>
  );
}

function LegendDot({ source }: { source: "local" | "mom" }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400">
      <span
        className="h-2.5 w-2.5 rounded-full"
        style={{ backgroundColor: SOURCE_STYLES[source].color }}
        aria-hidden="true"
      />
      {SOURCE_STYLES[source].label}
    </span>
  );
}

export function HomePage() {
  const map = useQuery({ queryKey: ["network", "baseline"], queryFn: () => fetchNetworkSpaces(), staleTime: 300_000 });
  const domains = useQuery({ queryKey: ["domains"], queryFn: fetchDomains, staleTime: 300_000 });
  const metrics = useQuery({ queryKey: ["metrics"], queryFn: fetchMetrics, staleTime: 60_000 });
  const solutions = useQuery({ queryKey: ["solutions"], queryFn: listSolutions, staleTime: 30_000 });

  const recent = (solutions.data ?? []).slice(0, 3);
  const online = !domains.isError && !metrics.isError;
  const m = map.data;

  return (
    <div className="space-y-10 py-4">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Open Hardware Manager</h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          Match open hardware designs to manufacturing facilities and explore the resulting supply
          chains.
        </p>
      </div>

      {/* Hero: the manufacturing network map. */}
      <section aria-labelledby="network-heading">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 id="network-heading" className="text-lg font-semibold text-foreground">
            Manufacturing network
          </h2>
          <div className="flex gap-3">
            <LegendDot source="local" />
            <LegendDot source="mom" />
          </div>
        </div>

        <div className="h-[440px] overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
          {map.isLoading && <LoadingState message="Loading the network map…" />}
          {map.isError && (
            <ErrorState
              description={map.error instanceof Error ? map.error.message : "Failed to load the map."}
              onRetry={() => map.refetch()}
            />
          )}
          {m && !map.isLoading && !map.isError && <NetworkMap spaces={m.spaces} />}
        </div>

        {m && (
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{buildNetworkSummary(m)}</p>
        )}
      </section>

      {/* Network + system stats. */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="OHM facilities" value={(m?.local_count ?? 0).toLocaleString()} />
        <StatCard
          label="Maps of Making"
          value={m?.mom_available ? (m?.mom_count ?? 0).toLocaleString() : "—"}
        />
        <StatCard label="Requests (1h)" value={(metrics.data?.recent_requests_1h ?? 0).toLocaleString()} />
        <StatCard label="Errors" value={(metrics.data?.total_errors ?? 0).toLocaleString()} />
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <GettingStarted />
        </div>

        <div className="space-y-8">
          <section aria-labelledby="recent-heading">
            <div className="mb-3 flex items-center justify-between">
              <h2 id="recent-heading" className="text-lg font-semibold text-foreground">
                Recent solutions
              </h2>
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

          <section aria-labelledby="system-heading">
            <h2 id="system-heading" className="mb-3 text-lg font-semibold text-foreground">
              System
            </h2>
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
              <div>
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">
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
    </div>
  );
}
