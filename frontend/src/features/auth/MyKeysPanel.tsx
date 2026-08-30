"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound } from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../components/ui/Toast";
import { FIELD, FIELD_SM, LABEL } from "../../components/ui/field";
import { PANEL } from "../../components/ui/surface";
import { SECTION_TITLE } from "../../components/ui/typography";
import { useAuth } from "../../context/AuthContext";
import {
  type APIKeyResponse,
  createApiKey,
  listApiKeys,
  renewApiKey,
  revokeApiKey,
  revokeOtherApiKeys,
} from "../../api/ohm/identity";
import { TokenOnce } from "./TokenOnce";

/** Expiry is only worth showing when it is close enough to act on. */
function expiryNote(expiresAt: string | null | undefined): string | null {
  if (!expiresAt) return null;
  const days = Math.ceil(
    (new Date(expiresAt).getTime() - Date.now()) / 86_400_000,
  );
  if (days < 0) return "expired";
  if (days === 0) return "expires today";
  if (days <= 30) return `expires in ${days} day${days === 1 ? "" : "s"}`;
  return null;
}

/**
 * Your keys, on your own account.
 *
 * Before this the whole identity surface was admin-gated, so someone who
 * registered had exactly one key for ever: no second one for the CLI, and no
 * way to kill one that leaked. Settings stays admin-only — this is the same
 * ability, scoped to the account making the request.
 */
export function MyKeysPanel() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const { user } = useAuth();
  const [name, setName] = useState("");
  const [created, setCreated] = useState<string | null>(null);

  const keys = useQuery({ queryKey: ["identity", "keys"], queryFn: listApiKeys });
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["identity", "keys"] });

  const create = useMutation<APIKeyResponse, Error, void>({
    mutationFn: () =>
      createApiKey({ name: name.trim(), permissions: ["read", "write"] }),
    onSuccess: (key) => {
      setCreated(key.token ?? null);
      setName("");
      void invalidate();
    },
    onError: (err: unknown) => showError(err),
  });

  const revoke = useMutation({
    mutationFn: revokeApiKey,
    onSuccess: () => {
      showSuccess("Key revoked");
      void invalidate();
    },
    onError: (err: unknown) => showError(err),
  });

  const renew = useMutation({
    mutationFn: renewApiKey,
    onSuccess: () => {
      showSuccess("Expiry extended", {
        description: "The token itself is unchanged.",
      });
      void invalidate();
    },
    onError: (err: unknown) => showError(err),
  });

  const revokeOthers = useMutation<string, Error, void>({
    mutationFn: () => revokeOtherApiKeys(),
    onSuccess: (message) => {
      showSuccess(message);
      void invalidate();
    },
    onError: (err: unknown) => showError(err),
  });

  const rows = (keys.data ?? []).filter((k) => !k.revoked);

  return (
    <section className={PANEL} aria-labelledby="my-keys">
      <h2 id="my-keys" className={SECTION_TITLE}>
        Your keys
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        One per device or script. Revoke any you no longer use — a key stays
        valid until it expires or you kill it.
      </p>

      {created && (
        <div className="mt-4">
          <TokenOnce
            token={created}
            description="It will not be shown again."
            onDismiss={() => setCreated(null)}
          />
        </div>
      )}

      {keys.isPending ? (
        <div className="py-6">
          <LoadingSpinner />
        </div>
      ) : (
        <ul className="mt-4 divide-y divide-border">
          {rows.map((key) => {
            const note = expiryNote(key.expires_at);
            const isCurrent = key.key_id === user?.key_id;
            return (
              <li
                key={key.key_id}
                className="flex flex-wrap items-center gap-2 py-2 text-sm"
              >
                <span className="flex-1 min-w-32 text-foreground">{key.name}</span>
                {isCurrent && <Badge variant="blue">this session</Badge>}
                {note && <Badge variant="yellow">{note}</Badge>}
                <button
                  type="button"
                  className={FIELD_SM}
                  onClick={() => renew.mutate(key.key_id)}
                >
                  Renew
                </button>
                <button
                  type="button"
                  className={FIELD_SM}
                  disabled={isCurrent}
                  // Revoking the key you are holding would sign you out mid-click
                  // with no way back except the recovery code.
                  title={isCurrent ? "Sign out instead — this is the key in use" : undefined}
                  onClick={() => revoke.mutate(key.key_id)}
                >
                  Revoke
                </button>
              </li>
            );
          })}
          {rows.length === 0 && (
            <li className="py-3 text-sm text-muted-foreground">
              No active keys on this account.
            </li>
          )}
        </ul>
      )}

      <form
        className="mt-4 flex flex-wrap items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim()) create.mutate();
        }}
      >
        <label className={`${LABEL} flex-1 min-w-48`}>
          New key name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="laptop-cli"
            className={`${FIELD} mt-1 w-full`}
          />
        </label>
        <button
          type="submit"
          disabled={!name.trim() || create.isPending}
          className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-accent disabled:opacity-50"
        >
          {create.isPending ? "Creating…" : "Create key"}
        </button>
      </form>

      <button
        type="button"
        className={`${FIELD_SM} mt-4`}
        onClick={() => revokeOthers.mutate()}
        disabled={revokeOthers.isPending}
      >
        <KeyRound aria-hidden="true" className="mr-1.5 inline h-4 w-4" />
        Revoke every key but this one
      </button>
    </section>
  );
}
