import { useState } from "react";
import { FIELD, FIELD_MONO, LABEL } from "../../components/ui/field";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listDirectory, publishDirectoryEntry } from "../../api/ohm/identity";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useAuth } from "../../context/AuthContext";

export function DirectoryPanel() {
  const queryClient = useQueryClient();
  const { reportAuthFailure } = useAuth();
  const [did, setDid] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [domain, setDomain] = useState("");

  const entries = useQuery({
    queryKey: ["identity", "directory"],
    queryFn: listDirectory,
  });

  const publish = useMutation({
    mutationFn: () =>
      publishDirectoryEntry({
        did: did.trim(),
        display_name: displayName.trim(),
        base_url: baseUrl.trim() || null,
        domain: domain.trim() || null,
      }),
    onSuccess: () => {
      setDid("");
      setDisplayName("");
      setBaseUrl("");
      setDomain("");
      void queryClient.invalidateQueries({
        queryKey: ["identity", "directory"],
      });
    },
    onError: reportAuthFailure,
  });

  return (
    <div className="space-y-6">
      <section
        aria-labelledby="directory-publish-heading"
        className="rounded-xl border border-border bg-card p-5"
      >
        <h2
          id="directory-publish-heading"
          className="text-lg font-semibold text-foreground"
        >
          Publish
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Trust-on-follow registry row for a known DID (peacetime posture).
        </p>
        <form
          className="mt-4 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (did.trim()) publish.mutate();
          }}
        >
          <label className={LABEL}>
            DID
            <input
              value={did}
              onChange={(e) => setDid(e.target.value)}
              className={`${FIELD_MONO} mt-1 w-full max-w-xl`}
              required
            />
          </label>
          <label className={LABEL}>
            Display name
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className={`${FIELD} mt-1 w-full max-w-md`}
            />
          </label>
          <label className={LABEL}>
            Base URL
            <input
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://ohm.example.org"
              className={`${FIELD} mt-1 w-full max-w-md`}
            />
          </label>
          <label className={LABEL}>
            Domain (optional)
            <input
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="example.org"
              className={`${FIELD} mt-1 w-full max-w-md`}
            />
          </label>
          <button
            type="submit"
            disabled={publish.isPending || !did.trim()}
            className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-accent disabled:opacity-50"
          >
            Publish
          </button>
          {publish.isError && (
            <p className="text-sm text-destructive" role="alert">
              {publish.error instanceof Error
                ? publish.error.message
                : "Publish failed"}
            </p>
          )}
          {publish.isSuccess && (
            <p className="text-sm text-success" role="status">
              Published {publish.data.did}
            </p>
          )}
        </form>
      </section>

      <section
        aria-labelledby="directory-list-heading"
        className="rounded-xl border border-border bg-card p-5"
      >
        <h2
          id="directory-list-heading"
          className="text-lg font-semibold text-foreground"
        >
          Directory
        </h2>
        {entries.isLoading && <LoadingSpinner message="Loading directory…" />}
        {entries.isError && (
          <p className="mt-3 text-sm text-destructive" role="alert">
            {entries.error.message}
          </p>
        )}
        {entries.data && (
          <ul className="mt-4 divide-y divide-border">
            {entries.data.map((e) => (
              <li key={e.did} className="py-3">
                <p className="font-medium text-foreground">
                  {e.display_name || "(unnamed)"}
                </p>
                <p className="mt-1 break-all font-mono text-xs text-muted-foreground">
                  {e.did}
                </p>
                {e.base_url && (
                  <p className="mt-1 break-all text-sm text-muted-foreground">
                    {e.base_url}
                  </p>
                )}
                {e.domain && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    domain {e.domain}
                  </p>
                )}
              </li>
            ))}
            {entries.data.length === 0 && (
              <li className="py-3 text-sm text-muted-foreground">
                No directory entries yet.
              </li>
            )}
          </ul>
        )}
      </section>
    </div>
  );
}
