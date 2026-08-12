import { useQuery } from "@tanstack/react-query";
import { fetchAllKitchens } from "../../api/ohm/kitchens";
import { LoadingState, EmptyState, ErrorState } from "../../components/ui/states";

/**
 * Cooking-domain kitchen browse: list-only (no facets, no create, no detail
 * page — see the cooking-domain-instance plan's "Out of scope"). Kitchens
 * are uploaded to storage directly, not created here.
 */
export function KitchenListView() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["kitchens"],
    queryFn: fetchAllKitchens,
  });

  const kitchens = data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Kitchens</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Kitchens available for matching on this cooking-domain instance.
        </p>
      </div>

      {isLoading && <LoadingState message="Loading kitchens…" />}
      {isError && (
        <ErrorState
          description={error instanceof Error ? error.message : "Failed to load kitchens."}
          onRetry={() => refetch()}
        />
      )}
      {!isLoading && !isError && kitchens.length === 0 && (
        <EmptyState
          icon="🍽️"
          title="No kitchens yet"
          description="Upload kitchen JSON to this instance's storage under okw/ to see them here."
        />
      )}
      {!isLoading && !isError && kitchens.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {kitchens.map((kitchen) => (
            <div
              key={kitchen.id}
              className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900"
            >
              <h2 className="font-semibold text-foreground">{kitchen.name}</h2>
              <p className="mt-2 text-xs text-muted-foreground">
                {kitchen.appliances.length} appliance
                {kitchen.appliances.length !== 1 ? "s" : ""} · {kitchen.tools.length} tool
                {kitchen.tools.length !== 1 ? "s" : ""}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
