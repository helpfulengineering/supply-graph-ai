import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchFederationStatus,
  seedFromPeerUrl,
} from "../../api/ohm/federation";
import { Button } from "../../components/ui/button";
import { useAuth } from "../../context/AuthContext";

/**
 * Optional Network CTA: follow configured seed peer + OKW sync.
 * Hidden when federation is off or seed_peer_url is empty.
 */
export function SeedPeerCta() {
  const queryClient = useQueryClient();
  const { hasWrite, reportAuthFailure } = useAuth();
  const status = useQuery({
    queryKey: ["federation", "status"],
    queryFn: fetchFederationStatus,
    retry: false,
    staleTime: 60_000,
  });

  const seed = useMutation({
    mutationFn: (url: string) => seedFromPeerUrl(url),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["federation"] });
      await queryClient.invalidateQueries({ queryKey: ["network"] });
    },
    onError: reportAuthFailure,
  });

  if (status.isLoading || status.isError) return null;

  const seedUrl = status.data?.seed_peer_url?.trim();
  if (!seedUrl) return null;

  return (
    <div
      role="region"
      aria-label="Seed facilities from peer"
      className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm dark:border-slate-700 dark:bg-slate-900"
    >
      <p className="font-medium text-foreground">Seed local facilities from a public peer</p>
      <p className="mt-1 text-xs text-muted-foreground">
        Follow{" "}
        <code className="text-xs">{seedUrl}</code> and sync OKW copies you can edit on this
        node. Edits stay local — peers keep their own copies.
      </p>
      {!hasWrite && (
        <p className="mt-2 text-xs text-amber-800 dark:text-amber-200">
          Syncing requires a write-capable API key.
        </p>
      )}
      {seed.isError && (
        <p className="mt-2 text-xs text-red-600" role="alert">
          {seed.error instanceof Error ? seed.error.message : "Seed sync failed."}
        </p>
      )}
      {seed.isSuccess && (
        <p className="mt-2 text-xs text-green-700 dark:text-green-300" role="status">
          Synced {seed.data.okwPulled} OKW record
          {seed.data.okwPulled === 1 ? "" : "s"}
          {seed.data.okhPulled
            ? ` (+ ${seed.data.okhPulled} OKH)`
            : ""}
          .
        </p>
      )}
      <div className="mt-3">
        <Button
          size="sm"
          disabled={!hasWrite || seed.isPending}
          onClick={() => seed.mutate(seedUrl)}
        >
          {seed.isPending ? "Seeding…" : "Follow & sync seed peer"}
        </Button>
      </div>
    </div>
  );
}
