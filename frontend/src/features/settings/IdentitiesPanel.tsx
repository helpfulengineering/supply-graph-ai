import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  fetchSecurityPolicy,
  getIdentity,
  listAccounts,
  mintIdentity,
  rotateIdentity,
  type Identity,
} from "../../api/ohm/identity";
import { Badge } from "../../components/ui/Badge";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useAuth } from "../../context/AuthContext";

function remember(id: Identity, replaceDid?: string) {
  return (prev: Identity[]) => [
    id,
    ...prev.filter((x) => x.did !== id.did && x.did !== replaceDid),
  ];
}

export function IdentitiesPanel() {
  const { reportAuthFailure } = useAuth();
  const [accountId, setAccountId] = useState("");
  const [kind, setKind] = useState<"person" | "space">("person");
  const [displayName, setDisplayName] = useState("");
  const [lookupDid, setLookupDid] = useState("");
  const [known, setKnown] = useState<Identity[]>([]);

  const policy = useQuery({
    queryKey: ["identity", "security-policy"],
    queryFn: fetchSecurityPolicy,
    staleTime: 5 * 60_000,
  });
  const accounts = useQuery({
    queryKey: ["identity", "accounts"],
    queryFn: listAccounts,
  });

  const mintAllowed = policy.data?.custodial_keys_allowed !== false;

  const mint = useMutation({
    mutationFn: () =>
      mintIdentity({
        account_id: accountId,
        kind,
        display_name: displayName.trim(),
      }),
    onSuccess: (id) => {
      setKnown(remember(id));
      setDisplayName("");
    },
    onError: reportAuthFailure,
  });

  const lookup = useMutation({
    mutationFn: () => getIdentity(lookupDid.trim()),
    onSuccess: (id) => setKnown(remember(id)),
    onError: reportAuthFailure,
  });

  const rotate = useMutation({
    mutationFn: (did: string) => rotateIdentity(did),
    onSuccess: (id, oldDid) => setKnown(remember(id, oldDid)),
    onError: reportAuthFailure,
  });

  return (
    <div className="space-y-8">
      <section
        aria-labelledby="mint-heading"
        className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <h2 id="mint-heading" className="text-lg font-semibold text-foreground">
          Mint identity
        </h2>
        {!mintAllowed && (
          <p className="mt-2 text-sm text-amber-800 dark:text-amber-200" role="status">
            Custodial key minting is disabled by this node&apos;s security policy.
          </p>
        )}
        <form
          className="mt-4 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (accountId && mintAllowed) mint.mutate();
          }}
        >
          <label className="block text-sm font-medium">
            Account
            <select
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              className="mt-1 block w-full max-w-md rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
              required
              disabled={!mintAllowed}
            >
              <option value="">Select account…</option>
              {(accounts.data ?? [])
                .filter((a) => a.id && !a.disabled)
                .map((a) => (
                  <option key={a.id} value={a.id!}>
                    {a.display_name} ({a.id})
                  </option>
                ))}
            </select>
          </label>
          <label className="block text-sm font-medium">
            Kind
            <select
              value={kind}
              onChange={(e) => setKind(e.target.value as "person" | "space")}
              className="mt-1 block rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
              disabled={!mintAllowed}
            >
              <option value="person">person</option>
              <option value="space">space</option>
            </select>
          </label>
          <label className="block text-sm font-medium">
            Display name
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="mt-1 w-full max-w-md rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
              disabled={!mintAllowed}
            />
          </label>
          <button
            type="submit"
            disabled={!mintAllowed || mint.isPending || !accountId}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            Mint
          </button>
          {mint.isError && (
            <p className="text-sm text-red-600" role="alert">
              {mint.error instanceof Error ? mint.error.message : "Mint failed"}
            </p>
          )}
        </form>
      </section>

      <section
        aria-labelledby="lookup-heading"
        className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <h2 id="lookup-heading" className="text-lg font-semibold text-foreground">
          Look up DID
        </h2>
        <form
          className="mt-4 flex flex-wrap items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (lookupDid.trim()) lookup.mutate();
          }}
        >
          <label className="block min-w-[16rem] flex-1 text-sm font-medium">
            DID
            <input
              value={lookupDid}
              onChange={(e) => setLookupDid(e.target.value)}
              placeholder="did:key:…"
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm dark:border-slate-600 dark:bg-slate-950"
              required
            />
          </label>
          <button
            type="submit"
            disabled={lookup.isPending || !lookupDid.trim()}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            Show
          </button>
        </form>
        {lookup.isError && (
          <p className="mt-2 text-sm text-red-600" role="alert">
            {lookup.error instanceof Error ? lookup.error.message : "Lookup failed"}
          </p>
        )}
      </section>

      {known.length > 0 && (
        <section
          aria-labelledby="known-heading"
          className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
        >
          <h2 id="known-heading" className="text-lg font-semibold text-foreground">
            Identities
          </h2>
          {lookup.isPending && <LoadingSpinner message="Loading…" />}
          <ul className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
            {known.map((id) => (
              <li key={id.did} className="flex flex-wrap items-start justify-between gap-2 py-3">
                <div className="min-w-0">
                  <p className="font-medium text-foreground">
                    {id.display_name || "(unnamed)"}
                  </p>
                  <p className="break-all font-mono text-xs text-slate-500">{id.did}</p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    <Badge variant="blue">{id.kind}</Badge>
                    {id.custodial && <Badge variant="default">custodial</Badge>}
                  </div>
                </div>
                <button
                  type="button"
                  className="rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-600"
                  disabled={rotate.isPending}
                  onClick={() => {
                    if (
                      window.confirm(
                        `Rotate key for ${id.did}? The DID will change; the old key links to the new one.`,
                      )
                    ) {
                      rotate.mutate(id.did);
                    }
                  }}
                >
                  Rotate
                </button>
              </li>
            ))}
          </ul>
          {rotate.isError && (
            <p className="mt-2 text-sm text-red-600" role="alert">
              {rotate.error instanceof Error ? rotate.error.message : "Rotate failed"}
            </p>
          )}
        </section>
      )}
    </div>
  );
}
