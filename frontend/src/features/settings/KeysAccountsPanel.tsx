import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createAccount,
  createApiKey,
  disableAccount,
  listAccounts,
  listApiKeys,
  revokeApiKey,
} from "../../api/ohm/identity";
import { Badge } from "../../components/ui/Badge";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useAuth } from "../../context/AuthContext";

const PERMISSION_OPTIONS = ["read", "write", "admin"] as const;

export function KeysAccountsPanel() {
  const queryClient = useQueryClient();
  const { reportAuthFailure } = useAuth();
  const [keyName, setKeyName] = useState("");
  const [permissions, setPermissions] = useState<string[]>(["read"]);
  const [createdToken, setCreatedToken] = useState<string | null>(null);
  const [accountName, setAccountName] = useState("");
  const [accountKind, setAccountKind] = useState<"person" | "space">("person");

  const keys = useQuery({
    queryKey: ["identity", "keys"],
    queryFn: listApiKeys,
  });
  const accounts = useQuery({
    queryKey: ["identity", "accounts"],
    queryFn: listAccounts,
  });

  const createKey = useMutation({
    mutationFn: () => createApiKey({ name: keyName.trim(), permissions }),
    onSuccess: (res) => {
      setCreatedToken(res.token ?? null);
      setKeyName("");
      void queryClient.invalidateQueries({ queryKey: ["identity", "keys"] });
    },
    onError: reportAuthFailure,
  });

  const revoke = useMutation({
    mutationFn: (keyId: string) => revokeApiKey(keyId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["identity", "keys"] }),
    onError: reportAuthFailure,
  });

  const createAcc = useMutation({
    mutationFn: () =>
      createAccount({ display_name: accountName.trim(), kind: accountKind }),
    onSuccess: () => {
      setAccountName("");
      void queryClient.invalidateQueries({ queryKey: ["identity", "accounts"] });
    },
    onError: reportAuthFailure,
  });

  const disableAcc = useMutation({
    mutationFn: (id: string) => disableAccount(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["identity", "accounts"] }),
    onError: reportAuthFailure,
  });

  function togglePermission(p: string) {
    setPermissions((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p],
    );
  }

  return (
    <div className="space-y-8">
      <p className="text-sm text-muted-foreground">
        To rotate a key: create a replacement, switch Session to it, then revoke the old key.
      </p>

      {createdToken && (
        <div
          role="dialog"
          aria-labelledby="token-once-heading"
          className="rounded-xl border border-amber-300 bg-amber-50 p-5 dark:border-amber-800 dark:bg-amber-950"
        >
          <h2 id="token-once-heading" className="text-lg font-semibold text-amber-950 dark:text-amber-100">
            Copy this token now
          </h2>
          <p className="mt-1 text-sm text-amber-900 dark:text-amber-200">
            It will not be shown again.
          </p>
          <pre className="mt-3 overflow-x-auto rounded-md bg-white p-3 font-mono text-xs dark:bg-slate-900">
            {createdToken}
          </pre>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white"
              onClick={() => void navigator.clipboard.writeText(createdToken)}
            >
              Copy
            </button>
            <button
              type="button"
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600"
              onClick={() => setCreatedToken(null)}
            >
              Done
            </button>
          </div>
        </div>
      )}

      <section
        aria-labelledby="keys-heading"
        className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <h2 id="keys-heading" className="text-lg font-semibold text-foreground">
          API keys
        </h2>

        <form
          className="mt-4 space-y-3 border-b border-slate-100 pb-4 dark:border-slate-800"
          onSubmit={(e) => {
            e.preventDefault();
            if (keyName.trim() && permissions.length) createKey.mutate();
          }}
        >
          <label className="block text-sm font-medium">
            Name
            <input
              value={keyName}
              onChange={(e) => setKeyName(e.target.value)}
              className="mt-1 w-full max-w-md rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
              required
            />
          </label>
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
          <button
            type="submit"
            disabled={createKey.isPending || !keyName.trim()}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            Create key
          </button>
          {createKey.isError && (
            <p className="text-sm text-red-600" role="alert">
              {createKey.error instanceof Error
                ? createKey.error.message
                : "Failed to create key"}
            </p>
          )}
        </form>

        {keys.isLoading && <LoadingSpinner message="Loading keys…" />}
        {keys.isError && (
          <p className="mt-3 text-sm text-red-600" role="alert">
            {keys.error.message}
          </p>
        )}
        {keys.data && (
          <ul className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
            {keys.data.map((k) => (
              <li key={k.key_id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div>
                  <p className="font-medium text-foreground">{k.name}</p>
                  <p className="font-mono text-xs text-slate-500">{k.key_id}</p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {k.permissions.map((p) => (
                      <Badge key={p} variant="blue">
                        {p}
                      </Badge>
                    ))}
                    {k.revoked && <Badge variant="red">revoked</Badge>}
                  </div>
                </div>
                {!k.revoked && (
                  <button
                    type="button"
                    className="rounded-md border border-red-300 px-2 py-1 text-sm text-red-700 hover:bg-red-50 dark:border-red-800 dark:text-red-300"
                    onClick={() => {
                      if (window.confirm(`Revoke key “${k.name}”?`)) {
                        revoke.mutate(k.key_id);
                      }
                    }}
                  >
                    Revoke
                  </button>
                )}
              </li>
            ))}
            {keys.data.length === 0 && (
              <li className="py-3 text-sm text-muted-foreground">No keys yet.</li>
            )}
          </ul>
        )}
      </section>

      <section
        aria-labelledby="accounts-heading"
        className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <h2 id="accounts-heading" className="text-lg font-semibold text-foreground">
          Accounts
        </h2>

        <form
          className="mt-4 space-y-3 border-b border-slate-100 pb-4 dark:border-slate-800"
          onSubmit={(e) => {
            e.preventDefault();
            if (accountName.trim()) createAcc.mutate();
          }}
        >
          <label className="block text-sm font-medium">
            Display name
            <input
              value={accountName}
              onChange={(e) => setAccountName(e.target.value)}
              className="mt-1 w-full max-w-md rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
              required
            />
          </label>
          <label className="block text-sm font-medium">
            Kind
            <select
              value={accountKind}
              onChange={(e) => setAccountKind(e.target.value as "person" | "space")}
              className="mt-1 block rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
            >
              <option value="person">person</option>
              <option value="space">space</option>
            </select>
          </label>
          <button
            type="submit"
            disabled={createAcc.isPending || !accountName.trim()}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            Create account
          </button>
        </form>

        {accounts.isLoading && <LoadingSpinner message="Loading accounts…" />}
        {accounts.data && (
          <ul className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
            {accounts.data.map((a) => (
              <li
                key={a.id ?? a.display_name}
                className="flex flex-wrap items-center justify-between gap-2 py-3"
              >
                <div>
                  <p className="font-medium text-foreground">{a.display_name}</p>
                  <p className="text-xs text-slate-500">
                    {a.kind}
                    {a.id ? ` · ${a.id}` : ""}
                  </p>
                  {a.disabled && <Badge variant="red">disabled</Badge>}
                </div>
                {a.id && !a.disabled && (
                  <button
                    type="button"
                    className="rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-600"
                    onClick={() => {
                      if (window.confirm(`Disable account “${a.display_name}”?`)) {
                        disableAcc.mutate(a.id!);
                      }
                    }}
                  >
                    Disable
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
