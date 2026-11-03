"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listInvites, mintInvite, revokeInvite } from "../../api/ohm/identity";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useAuth } from "../../context/AuthContext";
import { PANEL } from "../../components/ui/surface";
import { SECTION_TITLE } from "../../components/ui/typography";

export function InvitesPanel() {
  const queryClient = useQueryClient();
  const { reportAuthFailure } = useAuth();
  const [ttlDays, setTtlDays] = useState("7");
  const [useLimit, setUseLimit] = useState("");
  const [link, setLink] = useState<string | null>(null);
  const invites = useQuery({
    queryKey: ["identity", "invites"],
    queryFn: listInvites,
  });
  const mint = useMutation({
    mutationFn: () =>
      mintInvite({
        ttl_days: Number(ttlDays),
        use_limit: useLimit.trim() ? Number(useLimit) : null,
      }),
    onSuccess: (minted) => {
      setLink(`/register?invite=${minted.token}`);
      void queryClient.invalidateQueries({ queryKey: ["identity", "invites"] });
    },
    onError: reportAuthFailure,
  });
  const revoke = useMutation({
    mutationFn: (inviteId: string) => revokeInvite(inviteId),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["identity", "invites"] }),
    onError: reportAuthFailure,
  });

  if (invites.isPending) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <section className={PANEL}>
      <h2 className={SECTION_TITLE}>Invites</h2>
      <form
        className="mt-3 flex flex-wrap items-end gap-3 text-sm"
        onSubmit={(e) => {
          e.preventDefault();
          mint.mutate();
        }}
      >
        <label>
          Expires in days
          <input
            value={ttlDays}
            onChange={(e) => setTtlDays(e.target.value)}
            type="number"
            min={1}
            required
            className="mt-1 block w-24"
          />
        </label>
        <label>
          Use limit
          <input
            value={useLimit}
            onChange={(e) => setUseLimit(e.target.value)}
            type="number"
            min={1}
            placeholder="None"
            className="mt-1 block w-24"
          />
        </label>
        <button type="submit" className="underline">
          Mint invite
        </button>
      </form>
      {link && <p className="mt-3 break-all font-mono text-xs">{link}</p>}
      <ul className="mt-3 space-y-2 text-sm">
        {(invites.data ?? []).map((row) => (
          <li key={row.invite_id} className="flex items-center gap-3">
            <span className="font-mono text-xs">{row.invite_id}</span>
            {row.revoked ? (
              <span>Revoked</span>
            ) : (
              <button
                type="button"
                onClick={() => revoke.mutate(row.invite_id)}
                className="text-sm underline"
              >
                Revoke
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
