import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  discoverFederationPeers,
  fetchFederationStatus,
  followFederationPeer,
  listFederationPeers,
  runFederationSync,
  unfollowFederationPeer,
} from "../../api/ohm/federation";
import { fetchSecurityPolicy } from "../../api/ohm/identity";
import { ApiError } from "../../api/ohm/client";
import { Badge } from "../../components/ui/Badge";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useAuth } from "../../context/AuthContext";

export function FederationPanel() {
  const queryClient = useQueryClient();
  const { reportAuthFailure } = useAuth();

  const status = useQuery({
    queryKey: ["federation", "status"],
    queryFn: fetchFederationStatus,
    retry: false,
  });
  const peers = useQuery({
    queryKey: ["federation", "peers"],
    queryFn: listFederationPeers,
    retry: false,
  });
  const policy = useQuery({
    queryKey: ["identity", "security-policy"],
    queryFn: fetchSecurityPolicy,
    staleTime: 5 * 60_000,
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["federation"] });
  };

  const discover = useMutation({
    mutationFn: discoverFederationPeers,
    onSuccess: invalidate,
    onError: reportAuthFailure,
  });
  const follow = useMutation({
    mutationFn: followFederationPeer,
    onSuccess: invalidate,
    onError: reportAuthFailure,
  });
  const unfollow = useMutation({
    mutationFn: unfollowFederationPeer,
    onSuccess: invalidate,
    onError: reportAuthFailure,
  });
  const sync = useMutation({
    mutationFn: runFederationSync,
    onSuccess: invalidate,
    onError: reportAuthFailure,
  });

  const disabled = federationDisabled(status.error) || federationDisabled(peers.error);
  const mdnsAdvertise = policy.data?.mdns_advertise !== false;

  return (
    <div className="space-y-8">
      {disabled && (
        <p className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
          Federation is not enabled on this server (set{" "}
          <code className="text-xs">OHM_FEDERATION_ENABLED=true</code>).
        </p>
      )}

      <section
        aria-labelledby="federation-status-heading"
        className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <h2 id="federation-status-heading" className="text-lg font-semibold text-foreground">
          Node status
        </h2>
        {status.isLoading && <LoadingSpinner message="Loading status…" />}
        {status.isError && !disabled && (
          <p className="mt-3 text-sm text-red-600" role="alert">
            {status.error.message}
          </p>
        )}
        {status.data && (
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs uppercase text-slate-500">DID</dt>
              <dd className="mt-1 break-all font-mono text-xs">{status.data.did}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-slate-500">Role</dt>
              <dd className="mt-1">{status.data.role}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-slate-500">Security mode</dt>
              <dd className="mt-1">{policy.data?.mode ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-slate-500">mDNS</dt>
              <dd className="mt-1 flex flex-wrap gap-1">
                <Badge variant={status.data.mdns_enabled ? "green" : "default"}>
                  {status.data.mdns_enabled ? "enabled" : "off"}
                </Badge>
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-slate-500">Peers</dt>
              <dd className="mt-1">
                {status.data.peer_count} known · {status.data.followed_peer_count} followed
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-slate-500">Catalog</dt>
              <dd className="mt-1">{status.data.catalog_record_count} records</dd>
            </div>
          </dl>
        )}
        {!mdnsAdvertise && (
          <p className="mt-4 text-sm text-amber-800 dark:text-amber-200" role="status">
            Shielded posture: mDNS advertise is off — this node will not announce itself on the
            LAN.
          </p>
        )}
      </section>

      <section
        aria-labelledby="federation-peers-heading"
        className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="federation-peers-heading" className="text-lg font-semibold text-foreground">
            Peers
          </h2>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={disabled || discover.isPending}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600 disabled:opacity-50"
              onClick={() => discover.mutate()}
            >
              {discover.isPending ? "Discovering…" : "Discover"}
            </button>
            <button
              type="button"
              disabled={disabled || sync.isPending}
              className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              onClick={() => sync.mutate(undefined)}
            >
              {sync.isPending ? "Syncing…" : "Sync followed"}
            </button>
          </div>
        </div>

        {peers.isLoading && <LoadingSpinner message="Loading peers…" />}
        {peers.isError && !disabled && (
          <p className="mt-3 text-sm text-red-600" role="alert">
            {peers.error.message}
          </p>
        )}
        {peers.data && peers.data.length === 0 && (
          <p className="mt-3 text-sm text-muted-foreground">
            No peers yet. Try Discover, or add manual peers in server config.
          </p>
        )}
        {peers.data && peers.data.length > 0 && (
          <ul className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
            {peers.data.map((p) => (
              <li
                key={p.did}
                className="flex flex-wrap items-start justify-between gap-3 py-3"
              >
                <div className="min-w-0">
                  <p className="font-medium text-foreground">
                    {p.display_name || p.did.slice(0, 24)}
                  </p>
                  <p className="mt-1 break-all font-mono text-xs text-slate-500">{p.did}</p>
                  <p className="mt-1 break-all text-xs text-slate-600 dark:text-slate-300">
                    {p.base_url}
                  </p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    <Badge variant="default">{p.source}</Badge>
                    {p.followed && <Badge variant="green">followed</Badge>}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {p.followed ? (
                    <button
                      type="button"
                      className="rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-600"
                      disabled={unfollow.isPending}
                      onClick={() => unfollow.mutate(p.did)}
                    >
                      Unfollow
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-600"
                      disabled={follow.isPending}
                      onClick={() => follow.mutate(p.did)}
                    >
                      Follow
                    </button>
                  )}
                  <button
                    type="button"
                    className="rounded-md bg-indigo-600 px-2 py-1 text-sm font-medium text-white disabled:opacity-50"
                    disabled={sync.isPending || !p.base_url}
                    onClick={() => sync.mutate(p.base_url)}
                  >
                    Sync
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}

        {sync.isSuccess && (
          <p className="mt-3 text-sm text-green-700 dark:text-green-300" role="status">
            Sync finished — pulled {sync.data.total_pulled} record(s) from{" "}
            {sync.data.results.length} peer(s).
          </p>
        )}
        {sync.isError && (
          <p className="mt-3 text-sm text-red-600" role="alert">
            {sync.error instanceof Error ? sync.error.message : "Sync failed"}
          </p>
        )}
      </section>
    </div>
  );
}

function federationDisabled(err: unknown): boolean {
  return err instanceof ApiError && err.status === 404;
}
