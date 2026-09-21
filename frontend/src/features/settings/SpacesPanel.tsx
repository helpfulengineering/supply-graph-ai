import { useEffect, useState } from "react";
import { FIELD_MONO, LABEL } from "../../components/ui/field";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "../../api/ohm/client";
import {
  claimSpace,
  fetchWhoami,
  listSpaceClaims,
  mintIdentity,
} from "../../api/ohm/identity";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useAuth } from "../../context/AuthContext";
import { PANEL } from "../../components/ui/surface";
import { SECTION_TITLE } from "../../components/ui/typography";

/**
 * A UX guard against an obvious typo (empty, missing prefix, pasted the
 * wrong thing) — not a cryptographic check. Deliberately loose about the
 * body: real did:key values are base58btc, but a strict alphabet check has
 * no business rejecting a well-formed DID over its key type or encoding.
 * The server is the real validator; this exists so a malformed value never
 * reaches "Claim".
 */
function isPlausibleDid(value: string): boolean {
  return /^did:key:z\S{6,}$/.test(value.trim());
}

function didFieldError(value: string, touched: boolean): string | null {
  if (!touched) return null;
  if (!value.trim()) return "Required.";
  if (!isPlausibleDid(value)) {
    return "Doesn't look like a DID — expected the form did:key:z6Mk…";
  }
  return null;
}

export function SpacesPanel() {
  const queryClient = useQueryClient();
  const { reportAuthFailure } = useAuth();
  const [spaceDid, setSpaceDid] = useState("");
  const [adminDid, setAdminDid] = useState("");
  const [spaceTouched, setSpaceTouched] = useState(false);
  const [adminTouched, setAdminTouched] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [claimNote, setClaimNote] = useState<string | null>(null);

  const whoami = useQuery({
    queryKey: ["identity", "whoami"],
    queryFn: fetchWhoami,
  });

  const claims = useQuery({
    queryKey: ["identity", "spaces"],
    queryFn: listSpaceClaims,
  });

  // Autofill from the session's own identity — the common case is claiming
  // as yourself. Only while the operator hasn't typed or cleared it
  // themselves; a session with no bound person DID (the bootstrap admin key)
  // gets the "mint one for me" action below instead.
  useEffect(() => {
    const did = whoami.data?.subject_did;
    if (did) {
      setAdminDid((prev) => (prev || adminTouched ? prev : did));
    }
  }, [whoami.data?.subject_did, adminTouched]);

  const mintPerson = useMutation({
    mutationFn: () =>
      mintIdentity({
        account_id: whoami.data!.account_id,
        kind: "person",
        display_name: whoami.data?.name || "Admin",
      }),
    onSuccess: (id) => {
      setAdminDid(id.did);
      setAdminTouched(true);
      setConfirmed(false);
    },
    onError: reportAuthFailure,
  });

  const mintSpace = useMutation({
    mutationFn: () =>
      mintIdentity({
        account_id: whoami.data!.account_id,
        kind: "space",
        display_name: "",
      }),
    onSuccess: (id) => {
      setSpaceDid(id.did);
      setSpaceTouched(true);
      setConfirmed(false);
    },
    onError: reportAuthFailure,
  });

  const claim = useMutation({
    mutationFn: () => claimSpace(spaceDid.trim(), adminDid.trim()),
    onSuccess: () => {
      setClaimNote(null);
      setSpaceDid("");
      setAdminDid("");
      setSpaceTouched(false);
      setAdminTouched(false);
      setConfirmed(false);
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

  const spaceError = didFieldError(spaceDid, spaceTouched);
  const adminError = didFieldError(adminDid, adminTouched);
  const bothValid = isPlausibleDid(spaceDid) && isPlausibleDid(adminDid);
  const canMint = Boolean(whoami.data?.account_id);

  return (
    <div className="space-y-6">
      <section aria-labelledby="claim-space-heading" className={PANEL}>
        <h2 id="claim-space-heading" className={SECTION_TITLE}>
          Claim space
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Bind a person DID as admin of a space DID. Whoever claims a space
          first becomes its admin (<abbr title="Trust On First Use">TOFU</abbr>{" "}
          — trust on first use) — there is no ownership to dispute
          beforehand, and this screen cannot undo a claim once it succeeds.
        </p>
        <form
          className="mt-4 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            setClaimNote(null);
            if (bothValid && confirmed) claim.mutate();
          }}
        >
          <div>
            <label className={LABEL}>
              Space DID
              <input
                value={spaceDid}
                onChange={(e) => {
                  setSpaceDid(e.target.value);
                  setConfirmed(false);
                }}
                onBlur={() => setSpaceTouched(true)}
                placeholder="did:key:z6Mk…"
                aria-invalid={spaceError ? true : undefined}
                aria-describedby="space-did-help"
                className={`${FIELD_MONO} mt-1 w-full max-w-xl`}
                required
              />
            </label>
            <p id="space-did-help" className="mt-1 text-xs text-muted-foreground">
              The space you&apos;re claiming. Creating a new one? Generate a
              fresh DID instead of inventing one.
            </p>
            {canMint && (
              <button
                type="button"
                className="mt-1 text-xs font-medium text-primary hover:underline disabled:opacity-50"
                disabled={mintSpace.isPending}
                onClick={() => mintSpace.mutate()}
              >
                {mintSpace.isPending
                  ? "Generating…"
                  : "Generate a new space DID"}
              </button>
            )}
            {spaceError && (
              <p className="mt-1 text-xs text-destructive" role="alert">
                {spaceError}
              </p>
            )}
          </div>

          <div>
            <label className={LABEL}>
              Admin DID (person)
              <input
                value={adminDid}
                onChange={(e) => {
                  setAdminDid(e.target.value);
                  setConfirmed(false);
                }}
                onBlur={() => setAdminTouched(true)}
                placeholder="did:key:z6Mk…"
                aria-invalid={adminError ? true : undefined}
                aria-describedby="admin-did-help"
                className={`${FIELD_MONO} mt-1 w-full max-w-xl`}
                required
              />
            </label>
            <p id="admin-did-help" className="mt-1 text-xs text-muted-foreground">
              Your person DID — shown at Settings → Identities, or mint one
              below if this session doesn&apos;t have one yet.
            </p>
            {canMint && !whoami.data?.subject_did && (
              <button
                type="button"
                className="mt-1 text-xs font-medium text-primary hover:underline disabled:opacity-50"
                disabled={mintPerson.isPending}
                onClick={() => mintPerson.mutate()}
              >
                {mintPerson.isPending
                  ? "Minting…"
                  : "Mint a person identity for me"}
              </button>
            )}
            {adminError && (
              <p className="mt-1 text-xs text-destructive" role="alert">
                {adminError}
              </p>
            )}
          </div>

          {(mintPerson.isError || mintSpace.isError) && (
            <p className="text-sm text-destructive" role="alert">
              {mintPerson.error instanceof Error
                ? mintPerson.error.message
                : mintSpace.error instanceof Error
                  ? mintSpace.error.message
                  : "Could not mint an identity"}
            </p>
          )}

          {bothValid && (
            <label className="flex items-start gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
                className="mt-0.5"
              />
              <span>
                This binds <span className="font-mono text-xs">{adminDid}</span>{" "}
                as admin of{" "}
                <span className="font-mono text-xs">{spaceDid}</span>. First
                claim wins and can&apos;t be undone from this screen.
              </span>
            </label>
          )}

          <button
            type="submit"
            disabled={claim.isPending || !bothValid || !confirmed}
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
        <p className="mt-4 text-xs text-muted-foreground">
          Need something this form doesn&apos;t cover? The full identity API
          is at{" "}
          <a href="/v1/docs" className="text-primary hover:underline">
            /v1/docs
          </a>
          .
        </p>
      </section>

      <section aria-labelledby="claims-heading" className={PANEL}>
        <h2 id="claims-heading" className={SECTION_TITLE}>
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
