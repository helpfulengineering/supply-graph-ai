import { useState } from "react";
import { FIELD_MONO } from "../../components/ui/field";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "../../api/ohm/client";
import { claimSpace, listSpaceClaims } from "../../api/ohm/identity";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useAuth } from "../../context/AuthContext";

export function SpacesPanel() {
  const queryClient = useQueryClient();
  const { reportAuthFailure } = useAuth();
  const [spaceDid, setSpaceDid] = useState("");
  const [adminDid, setAdminDid] = useState("");
  const [claimNote, setClaimNote] = useState<string | null>(null);

  const claims = useQuery({
    queryKey: ["identity", "spaces"],
    queryFn: listSpaceClaims,
  });

  const claim = useMutation({
    mutationFn: () => claimSpace(spaceDid.trim(), adminDid.trim()),
    onSuccess: () => {
      setClaimNote(null);
      setSpaceDid("");
      setAdminDid("");
      void queryClient.invalidateQueries({ queryKey: ["identity", "spaces"] });
    },
    onError: (err) => {
      reportAuthFailure(err);
      if (err instanceof ApiError && err.status === 409) {
        setClaimNote("Already claimed (TOFU)");
        return;
      }
      setClaimNote(err instanceof Error ? err.message : "Claim failed");
    },
  });

  return (
    <div className="space-y-6">
      <section
        aria-labelledby="claim-space-heading"
        className="rounded-xl border border-border bg-card p-5"
      >
        <h2
          id="claim-space-heading"
          className="text-lg font-semibold text-foreground"
        >
          Claim space
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Bind a person DID as admin of a space DID. First claimer wins (TOFU).
        </p>
        <form
          className="mt-4 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            setClaimNote(null);
            if (spaceDid.trim() && adminDid.trim()) claim.mutate();
          }}
        >
          <label className="block text-sm font-medium">
            Space DID
            <input
              value={spaceDid}
              onChange={(e) => setSpaceDid(e.target.value)}
              className={`${FIELD_MONO} mt-1 w-full max-w-xl`}
              required
            />
          </label>
          <label className="block text-sm font-medium">
            Admin DID (person)
            <input
              value={adminDid}
              onChange={(e) => setAdminDid(e.target.value)}
              className={`${FIELD_MONO} mt-1 w-full max-w-xl`}
              required
            />
          </label>
          <button
            type="submit"
            disabled={claim.isPending || !spaceDid.trim() || !adminDid.trim()}
            className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-accent disabled:opacity-50"
          >
            Claim
          </button>
          {claimNote && (
            <p
              className={
                claim.isError
                  ? "text-sm text-destructive"
                  : "text-sm text-warning"
              }
              role="alert"
            >
              {claimNote}
            </p>
          )}
          {claim.isSuccess && (
            <p className="text-sm text-success" role="status">
              Claimed {claim.data.space_did}
            </p>
          )}
        </form>
      </section>

      <section
        aria-labelledby="claims-heading"
        className="rounded-xl border border-border bg-card p-5"
      >
        <h2
          id="claims-heading"
          className="text-lg font-semibold text-foreground"
        >
          Space claims
        </h2>
        {claims.isLoading && <LoadingSpinner message="Loading claims…" />}
        {claims.isError && (
          <p className="mt-3 text-sm text-destructive" role="alert">
            {claims.error.message}
          </p>
        )}
        {claims.data && (
          <ul className="mt-4 divide-y divide-border">
            {claims.data.map((c) => (
              <li key={c.space_did} className="py-3">
                <p className="break-all font-mono text-xs text-foreground">
                  {c.space_did}
                </p>
                <p className="mt-1 break-all text-sm text-muted-foreground">
                  admin {c.admin_did}
                </p>
                {c.claimed_at && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    claimed {c.claimed_at}
                  </p>
                )}
              </li>
            ))}
            {claims.data.length === 0 && (
              <li className="py-3 text-sm text-muted-foreground">
                No space claims yet.
              </li>
            )}
          </ul>
        )}
      </section>
    </div>
  );
}
