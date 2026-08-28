"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/api/ohm/client";
import { listRemotePackages, pullPackage } from "@/api/ohm/package";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { PANEL_INSET, PANEL_WARNING } from "@/components/ui/surface";
import { CAPTION } from "@/components/ui/typography";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/utils";

/**
 * What the remote package store holds.
 *
 * The list beside this one shows only what THIS node built, which is the half
 * of "packages" that was missing: a node in a federation is usually interested
 * in what the others have.
 *
 * Most nodes have no remote configured, and that is not an error — it is a
 * capability the reader should learn exists. So the tab stays visible and says
 * so, the way the federation panel handles its own 404.
 */
export function RemotePackagesPanel() {
  const { hasWrite, reportAuthFailure } = useAuth();
  const { showSuccess } = useToast();
  const queryClient = useQueryClient();

  const remote = useQuery({
    queryKey: ["package-remote"],
    queryFn: listRemotePackages,
    retry: false,
    retryOnMount: false,
  });

  const pull = useMutation({
    mutationFn: (pkg: { name: string; version: string }) =>
      pullPackage(pkg.name, pkg.version),
    onSuccess: () => {
      showSuccess("Pulled into this node");
      void queryClient.invalidateQueries({ queryKey: ["package-list"] });
    },
    onError: reportAuthFailure,
  });

  if (remote.isPending) return <LoadingState message="Reading the remote…" />;

  if (remote.isError) {
    const status = (remote.error as ApiError)?.status;
    // 404 and 500 both mean "not configured here" in practice; a reader does
    // not need the distinction, and neither is a fault of theirs.
    if (status === 404 || status === 500) {
      return (
        <div className={cn(PANEL_WARNING, "p-3 text-sm")} role="status">
          Remote package storage is not configured on this node. An operator can
          set one up to share built packages with other nodes.
        </div>
      );
    }
    return (
      <ErrorState
        title="Could not reach the remote"
        description={(remote.error as Error)?.message}
        onRetry={() => void remote.refetch()}
      />
    );
  }

  if ((remote.data?.length ?? 0) === 0) {
    return (
      <EmptyState
        title="The remote holds no packages"
        description="Build a package here and push it to make it available to other nodes."
      />
    );
  }

  return (
    <div className="space-y-2">
      {remote.data?.map((pkg) => (
        <div
          key={`${pkg.name}@${pkg.version}`}
          className={cn(PANEL_INSET, "flex flex-wrap items-center gap-3")}
        >
          <span className="font-mono text-sm text-foreground">{pkg.name}</span>
          <span className={CAPTION}>{pkg.version}</span>
          {hasWrite && (
            <Button
              variant="outline"
              size="sm"
              className="ml-auto"
              disabled={pull.isPending}
              onClick={() =>
                pull.mutate({ name: pkg.name, version: pkg.version })
              }
            >
              Pull
            </Button>
          )}
        </div>
      ))}
    </div>
  );
}
