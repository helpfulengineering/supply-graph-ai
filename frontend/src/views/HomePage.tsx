import { useQuery } from "@tanstack/react-query";
import { PageHero } from "../components/layout/PageHero";
import { fetchDomains, fetchMetrics } from "../api/ohm/utility";
import { fetchNetworkSpaces } from "../api/ohm/network";
import { Badge } from "../components/ui/Badge";
import { LoadingState, ErrorState } from "../components/ui/states";
import { NetworkMap } from "../features/network/NetworkMapLazy";
import { GettingStarted } from "../features/dashboard/GettingStarted";
import { SecurityPolicyBadge } from "../features/settings/SecurityPolicyBadge";
import {
  buildNetworkSummary,
  SOURCE_STYLES,
  sourceColor,
} from "../features/network/networkSummary";

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <p className="text-2xl font-bold text-foreground">{value}</p>
      <p className="mt-0.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
    </div>
  );
}

function LegendDot({ source }: { source: "local" | "mom" }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
      <span
        className="h-2.5 w-2.5 rounded-full"
        style={{ backgroundColor: sourceColor(source) }}
        aria-hidden="true"
      />
      {SOURCE_STYLES[source].label}
    </span>
  );
}

export function HomePage() {
  const map = useQuery({
    queryKey: ["network", "baseline"],
    queryFn: () => fetchNetworkSpaces(),
  });
  const domains = useQuery({ queryKey: ["domains"], queryFn: fetchDomains });
  // Metrics are more volatile than the catalog data; keep a short stale window.
  const metrics = useQuery({
    queryKey: ["metrics"],
    queryFn: fetchMetrics,
    staleTime: 60_000,
  });

  const online = !domains.isError && !metrics.isError;
  const m = map.data;

  return (
    <div className="space-y-6">
      <div>
        <PageHero
          title="Open Hardware Manager"
          crumb="designs · facilities · supply chains"
        />
      </div>

      {/* Hero: the manufacturing network map. */}
      <section aria-labelledby="network-heading">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2
            id="network-heading"
            className="text-lg font-semibold text-foreground"
          >
            Manufacturing network
          </h2>
          <div className="flex gap-3">
            <LegendDot source="local" />
            <LegendDot source="mom" />
          </div>
        </div>

        <div className="h-[440px] overflow-hidden rounded-xl border border-border">
          {map.isLoading && <LoadingState message="Loading the network map…" />}
          {map.isError && (
            <ErrorState
              description={
                map.error instanceof Error
                  ? map.error.message
                  : "Failed to load the map."
              }
              onRetry={() => map.refetch()}
            />
          )}
          {m && !map.isLoading && !map.isError && (
            <NetworkMap spaces={m.spaces} />
          )}
        </div>

        {m && (
          <p className="mt-2 text-sm text-muted-foreground">
            {buildNetworkSummary(m)}
          </p>
        )}
      </section>

      {/* Network + system stats. */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="OHM facilities"
          value={(m?.local_count ?? 0).toLocaleString()}
        />
        <StatCard
          label="Maps of Making"
          value={m?.mom_available ? (m?.mom_count ?? 0).toLocaleString() : "—"}
        />
        <StatCard
          label="Requests (1h)"
          value={(metrics.data?.recent_requests_1h ?? 0).toLocaleString()}
        />
        <StatCard
          label="Errors"
          value={(metrics.data?.total_errors ?? 0).toLocaleString()}
        />
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <GettingStarted />
        </div>

        <div className="space-y-6">
          <section aria-labelledby="system-heading">
            <h2
              id="system-heading"
              className="mb-3 text-lg font-semibold text-foreground"
            >
              System
            </h2>
            <div className="space-y-3 rounded-xl border border-border bg-card p-5">
              <div className="flex items-center gap-2">
                <span
                  className={`h-2.5 w-2.5 rounded-full ${online ? "bg-success" : "bg-destructive"}`}
                  aria-hidden="true"
                />
                <span className="text-sm text-foreground">
                  {online ? "API online" : "API unreachable"}
                </span>
              </div>
              <div>
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Domains
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {(domains.data ?? []).map((d) => (
                    <Badge key={d.id} variant="blue">
                      {d.name}
                    </Badge>
                  ))}
                  {domains.isLoading && (
                    <span className="text-xs text-muted-foreground">
                      loading…
                    </span>
                  )}
                </div>
              </div>
              <div>
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Security
                </p>
                <SecurityPolicyBadge />
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
