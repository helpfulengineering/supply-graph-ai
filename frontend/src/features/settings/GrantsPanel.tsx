import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  bootstrapEdgeGrant,
  issueGrant,
  listGrants,
  revokeGrant,
} from "../../api/ohm/identity";
import { Badge } from "../../components/ui/Badge";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useAuth } from "../../context/AuthContext";

const PERMISSION_OPTIONS = ["read", "write", "admin"] as const;

export function GrantsPanel() {
  const queryClient = useQueryClient();
  const { reportAuthFailure } = useAuth();
  const [subjectDid, setSubjectDid] = useState("");
  const [listSubject, setListSubject] = useState("");
  const [permissions, setPermissions] = useState<string[]>(["read"]);
  const [scopeKind, setScopeKind] = useState("space");
  const [scopeTarget, setScopeTarget] = useState("");
  const [ttlDays, setTtlDays] = useState("");

  const grants = useQuery({
    queryKey: ["identity", "grants", listSubject],
    queryFn: () => listGrants(listSubject),
    enabled: Boolean(listSubject),
  });

  const issue = useMutation({
    mutationFn: () =>
      issueGrant({
        subject_did: subjectDid.trim(),
        permissions,
        scope: { kind: scopeKind, target: scopeTarget.trim(), v: 1 },
        ttl_days: ttlDays.trim() ? Number(ttlDays) : null,
      }),
    onSuccess: () => {
      const did = subjectDid.trim();
      setListSubject(did);
      void queryClient.invalidateQueries({ queryKey: ["identity", "grants", did] });
      setScopeTarget("");
    },
    onError: reportAuthFailure,
  });

  const revoke = useMutation({
    mutationFn: (grantId: string) => revokeGrant(grantId),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["identity", "grants", listSubject] }),
    onError: reportAuthFailure,
  });

  const bootstrap = useMutation({
    mutationFn: () => bootstrapEdgeGrant(subjectDid.trim()),
    onSuccess: () => {
      const did = subjectDid.trim();
      setListSubject(did);
      void queryClient.invalidateQueries({ queryKey: ["identity", "grants", did] });
    },
    onError: reportAuthFailure,
  });

  function togglePermission(p: string) {
    setPermissions((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p],
    );
  }

  return (
    <div className="space-y-8">
      <section
        aria-labelledby="list-grants-heading"
        className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <h2 id="list-grants-heading" className="text-lg font-semibold text-foreground">
          List grants
        </h2>
        <form
          className="mt-4 flex flex-wrap items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (subjectDid.trim()) setListSubject(subjectDid.trim());
          }}
        >
          <label className="block min-w-[16rem] flex-1 text-sm font-medium">
            Subject DID
            <input
              value={subjectDid}
              onChange={(e) => setSubjectDid(e.target.value)}
              placeholder="did:key:…"
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm dark:border-slate-600 dark:bg-slate-950"
            />
          </label>
          <button
            type="submit"
            disabled={!subjectDid.trim()}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            Load
          </button>
        </form>

        {grants.isLoading && <LoadingSpinner message="Loading grants…" />}
        {grants.isError && (
          <p className="mt-3 text-sm text-red-600" role="alert">
            {grants.error.message}
          </p>
        )}
        {grants.data && (
          <ul className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
            {grants.data.map((g) => (
              <li
                key={g.grant_id ?? `${g.subject_did}-${g.issued_at}`}
                className="flex flex-wrap items-start justify-between gap-2 py-3"
              >
                <div className="min-w-0">
                  <p className="font-mono text-xs text-slate-500">{g.grant_id}</p>
                  <p className="mt-1 text-sm text-foreground">
                    {g.scope.kind}:{g.scope.target}
                  </p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {(g.permissions ?? []).map((p) => (
                      <Badge key={p} variant="blue">
                        {p}
                      </Badge>
                    ))}
                  </div>
                  {g.expires_at && (
                    <p className="mt-1 text-xs text-slate-500">expires {g.expires_at}</p>
                  )}
                </div>
                {g.grant_id && (
                  <button
                    type="button"
                    className="rounded-md border border-red-300 px-2 py-1 text-sm text-red-700 hover:bg-red-50 dark:border-red-800 dark:text-red-300"
                    onClick={() => {
                      if (window.confirm("Revoke this grant?")) {
                        revoke.mutate(g.grant_id!);
                      }
                    }}
                  >
                    Revoke
                  </button>
                )}
              </li>
            ))}
            {grants.data.length === 0 && (
              <li className="py-3 text-sm text-muted-foreground">No grants for this subject.</li>
            )}
          </ul>
        )}
      </section>

      <section
        aria-labelledby="issue-grant-heading"
        className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <h2 id="issue-grant-heading" className="text-lg font-semibold text-foreground">
          Issue grant
        </h2>
        <form
          className="mt-4 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (subjectDid.trim() && scopeTarget.trim() && permissions.length) {
              issue.mutate();
            }
          }}
        >
          <p className="text-sm text-muted-foreground">
            Uses the Subject DID field above. Issuer defaults to the local node identity.
          </p>
          <fieldset>
            <legend className="text-sm font-medium">Permissions</legend>
            <div className="mt-2 flex flex-wrap gap-3">
              {PERMISSION_OPTIONS.map((p) => (
                <label key={p} className="flex items-center gap-1.5 text-sm">
                  <input
                    type="checkbox"
                    checked={permissions.includes(p)}
                    onChange={() => togglePermission(p)}
                  />
                  {p}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="block text-sm font-medium">
            Scope kind
            <select
              value={scopeKind}
              onChange={(e) => setScopeKind(e.target.value)}
              className="mt-1 block rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
            >
              <option value="node">node</option>
              <option value="space">space</option>
              <option value="pool">pool</option>
              <option value="record">record</option>
            </select>
          </label>
          <label className="block text-sm font-medium">
            Scope target
            <input
              value={scopeTarget}
              onChange={(e) => setScopeTarget(e.target.value)}
              placeholder="DID, pool id, or content hash"
              className="mt-1 w-full max-w-md rounded-md border border-slate-300 px-3 py-2 font-mono text-sm dark:border-slate-600 dark:bg-slate-950"
              required
            />
          </label>
          <label className="block text-sm font-medium">
            TTL (days, optional)
            <input
              type="number"
              min={1}
              value={ttlDays}
              onChange={(e) => setTtlDays(e.target.value)}
              className="mt-1 w-32 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
            />
          </label>
          <button
            type="submit"
            disabled={
              issue.isPending || !subjectDid.trim() || !scopeTarget.trim() || !permissions.length
            }
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            Issue
          </button>
          {issue.isError && (
            <p className="text-sm text-red-600" role="alert">
              {issue.error instanceof Error ? issue.error.message : "Issue failed"}
            </p>
          )}
          {issue.isSuccess && (
            <p className="text-sm text-green-700 dark:text-green-300" role="status">
              Issued grant {issue.data.grant_id}
            </p>
          )}
        </form>
      </section>

      <section
        aria-labelledby="bootstrap-heading"
        className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <h2 id="bootstrap-heading" className="text-lg font-semibold text-foreground">
          Bootstrap edge grant
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Subject DID above self-issues write on the local node scope (isolated-edge genesis).
        </p>
        <button
          type="button"
          disabled={bootstrap.isPending || !subjectDid.trim()}
          className="mt-4 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          onClick={() => bootstrap.mutate()}
        >
          Bootstrap
        </button>
        {bootstrap.isError && (
          <p className="mt-2 text-sm text-red-600" role="alert">
            {bootstrap.error instanceof Error ? bootstrap.error.message : "Bootstrap failed"}
          </p>
        )}
        {bootstrap.isSuccess && (
          <p className="mt-2 text-sm text-green-700 dark:text-green-300" role="status">
            Bootstrapped {bootstrap.data.grant_id}
          </p>
        )}
      </section>
    </div>
  );
}
