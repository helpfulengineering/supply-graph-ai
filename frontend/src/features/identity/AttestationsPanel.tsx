import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listAttestations } from "../../api/ohm/identity";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useAuth } from "../../context/AuthContext";
import { AttestationList } from "./AttestationList";

interface Props {
  /** When set, loads attestations for this content / bundle hash. */
  contentHash?: string | null;
}

/** Admin-only list of attestations for a content hash (package pin / design). */
export function AttestationsPanel({ contentHash }: Props) {
  const { isAdmin } = useAuth();
  const [lookup, setLookup] = useState("");
  const [activeHash, setActiveHash] = useState("");

  const hash = (contentHash?.trim() || activeHash).trim();

  const query = useQuery({
    queryKey: ["identity", "attestations", hash],
    queryFn: () => listAttestations({ content_hash: hash }),
    enabled: isAdmin && Boolean(hash),
    retry: false,
  });

  if (!isAdmin) return null;

  return (
    <section
      aria-labelledby="attestations-heading"
      className="rounded-xl border border-border bg-card p-5"
    >
      <h2
        id="attestations-heading"
        className="text-lg font-semibold text-foreground"
      >
        Attestations
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Signed facts about this content (type, issuer, time — no scores).
      </p>

      {!contentHash && (
        <form
          className="mt-4 flex flex-wrap items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (lookup.trim()) setActiveHash(lookup.trim());
          }}
        >
          <label className="block min-w-[16rem] flex-1 text-sm font-medium">
            Content hash
            <input
              value={lookup}
              onChange={(e) => setLookup(e.target.value)}
              placeholder="sha256:…"
              className="mt-1 w-full rounded-md border border-border px-3 py-2 font-mono text-sm bg-background"
            />
          </label>
          <button
            type="submit"
            disabled={!lookup.trim()}
            className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-accent disabled:opacity-50"
          >
            Load
          </button>
        </form>
      )}

      {hash && query.isLoading && (
        <LoadingSpinner message="Loading attestations…" />
      )}
      {hash && query.isError && (
        <p className="mt-3 text-sm text-destructive" role="alert">
          {query.error instanceof Error
            ? query.error.message
            : "Failed to load"}
        </p>
      )}
      {hash && query.data && (
        <div className="mt-4">
          <AttestationList items={query.data} />
        </div>
      )}
      {!hash && (
        <p className="mt-3 text-sm text-muted-foreground">
          Pin a package or enter a content hash to list attestations.
        </p>
      )}
    </section>
  );
}
