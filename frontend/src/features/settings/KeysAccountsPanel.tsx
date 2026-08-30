import { useState } from "react";
import {
  CHECKBOX,
  CHOICE_ROW,
  FIELD,
  LABEL,
} from "../../components/ui/field";
import { cn } from "@/lib/utils";
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
import { PANEL } from "../../components/ui/surface";
import { SECTION_TITLE } from "../../components/ui/typography";
import { TokenOnce } from "../auth/TokenOnce";

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
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["identity", "keys"] }),
    onError: reportAuthFailure,
  });

  const createAcc = useMutation({
    mutationFn: () =>
      createAccount({ display_name: accountName.trim(), kind: accountKind }),
    onSuccess: () => {
      setAccountName("");
      void queryClient.invalidateQueries({
        queryKey: ["identity", "accounts"],
      });
    },
    onError: reportAuthFailure,
  });

  const disableAcc = useMutation({
    mutationFn: (id: string) => disableAccount(id),
    onSuccess: () =>
      void queryClient.invalidateQueries({
        queryKey: ["identity", "accounts"],
      }),
    onError: reportAuthFailure,
  });

  function togglePermission(p: string) {
    setPermissions((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p],
    );
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        To rotate a key: create a replacement, switch Session to it, then revoke
        the old key.
      </p>

      {createdToken && (
        <TokenOnce
          token={createdToken}
          description="It will not be shown again."
          onDismiss={() => setCreatedToken(null)}
        />
      )}

      <section aria-labelledby="keys-heading" className={PANEL}>
        <h2 id="keys-heading" className={SECTION_TITLE}>
          API keys
        </h2>

        <form
          className="mt-4 space-y-3 border-b border-border pb-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (keyName.trim() && permissions.length) createKey.mutate();
          }}
        >
          <label className={LABEL}>
            Name
            <input
              value={keyName}
              onChange={(e) => setKeyName(e.target.value)}
              className={`${FIELD} mt-1 w-full max-w-md`}
              required
            />
          </label>
          <fieldset className="min-w-0">
            <legend className="text-sm font-medium">Permissions</legend>
            <div className="mt-2 flex flex-wrap gap-3">
              {PERMISSION_OPTIONS.map((p) => (
                <label key={p} className={cn(CHOICE_ROW, "w-auto")}>
                  <input
                    type="checkbox"
                    className={CHECKBOX}
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
            className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-accent disabled:opacity-50"
          >
            Create key
          </button>
          {createKey.isError && (
            <p className="text-sm text-destructive" role="alert">
              {createKey.error instanceof Error
                ? createKey.error.message
                : "Failed to create key"}
            </p>
          )}
        </form>

        {keys.isLoading && <LoadingSpinner message="Loading keys…" />}
        {keys.isError && (
          <p className="mt-3 text-sm text-destructive" role="alert">
            {keys.error.message}
          </p>
        )}
        {keys.data && (
          <ul className="mt-4 divide-y divide-border">
            {keys.data.map((k) => (
              <li
                key={k.key_id}
                className="flex flex-wrap items-center justify-between gap-2 py-3"
              >
                <div>
                  <p className="font-medium text-foreground">{k.name}</p>
                  <p className="font-mono text-xs text-muted-foreground">
                    {k.key_id}
                  </p>
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
                    className={`${FIELD} border-destructive text-destructive hover:bg-destructive/10`}
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
              <li className="py-3 text-sm text-muted-foreground">
                No keys yet.
              </li>
            )}
          </ul>
        )}
      </section>

      <section aria-labelledby="accounts-heading" className={PANEL}>
        <h2 id="accounts-heading" className={SECTION_TITLE}>
          Accounts
        </h2>

        <form
          className="mt-4 space-y-3 border-b border-border pb-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (accountName.trim()) createAcc.mutate();
          }}
        >
          <label className={LABEL}>
            Display name
            <input
              value={accountName}
              onChange={(e) => setAccountName(e.target.value)}
              className={`${FIELD} mt-1 w-full max-w-md`}
              required
            />
          </label>
          <label className={LABEL}>
            Kind
            <select
              value={accountKind}
              onChange={(e) =>
                setAccountKind(e.target.value as "person" | "space")
              }
              className={`${FIELD} mt-1 block`}
            >
              <option value="person">person</option>
              <option value="space">space</option>
            </select>
          </label>
          <button
            type="submit"
            disabled={createAcc.isPending || !accountName.trim()}
            className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-accent disabled:opacity-50"
          >
            Create account
          </button>
        </form>

        {accounts.isLoading && <LoadingSpinner message="Loading accounts…" />}
        {accounts.data && (
          <ul className="mt-4 divide-y divide-border">
            {accounts.data.map((a) => (
              <li
                key={a.id ?? a.display_name}
                className="flex flex-wrap items-center justify-between gap-2 py-3"
              >
                <div>
                  <p className="font-medium text-foreground">
                    {a.display_name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {a.kind}
                    {a.id ? ` · ${a.id}` : ""}
                  </p>
                  {a.disabled && <Badge variant="red">disabled</Badge>}
                </div>
                {a.id && !a.disabled && (
                  <button
                    type="button"
                    className={FIELD}
                    onClick={() => {
                      if (
                        window.confirm(`Disable account “${a.display_name}”?`)
                      ) {
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
