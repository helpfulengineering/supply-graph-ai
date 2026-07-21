import { useState } from "react";
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
      void queryClient.invalidateQueries({ queryKey: ["identity", "directory"] });
    },
    onError: reportAuthFailure,
  });

  return (
    <div className="space-y-8">
      <section
        aria-labelledby="directory-publish-heading"
        className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <h2 id="directory-publish-heading" className="text-lg font-semibold text-foreground">
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
          <label className="block text-sm font-medium">
            DID
            <input
              value={did}
              onChange={(e) => setDid(e.target.value)}
              className="mt-1 w-full max-w-xl rounded-md border border-slate-300 px-3 py-2 font-mono text-sm dark:border-slate-600 dark:bg-slate-950"
              required
            />
          </label>
          <label className="block text-sm font-medium">
            Display name
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="mt-1 w-full max-w-md rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
            />
          </label>
          <label className="block text-sm font-medium">
            Base URL
            <input
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://ohm.example.org"
              className="mt-1 w-full max-w-md rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
            />
          </label>
          <label className="block text-sm font-medium">
            Domain (optional)
            <input
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="example.org"
              className="mt-1 w-full max-w-md rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
            />
          </label>
          <button
            type="submit"
            disabled={publish.isPending || !did.trim()}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            Publish
          </button>
          {publish.isError && (
            <p className="text-sm text-red-600" role="alert">
              {publish.error instanceof Error ? publish.error.message : "Publish failed"}
            </p>
          )}
          {publish.isSuccess && (
            <p className="text-sm text-green-700 dark:text-green-300" role="status">
              Published {publish.data.did}
            </p>
          )}
        </form>
      </section>

      <section
        aria-labelledby="directory-list-heading"
        className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <h2 id="directory-list-heading" className="text-lg font-semibold text-foreground">
          Directory
        </h2>
        {entries.isLoading && <LoadingSpinner message="Loading directory…" />}
        {entries.isError && (
          <p className="mt-3 text-sm text-red-600" role="alert">
            {entries.error.message}
          </p>
        )}
        {entries.data && (
          <ul className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
            {entries.data.map((e) => (
              <li key={e.did} className="py-3">
                <p className="font-medium text-foreground">{e.display_name || "(unnamed)"}</p>
                <p className="mt-1 break-all font-mono text-xs text-slate-500">{e.did}</p>
                {e.base_url && (
                  <p className="mt-1 break-all text-sm text-slate-600 dark:text-slate-300">
                    {e.base_url}
                  </p>
                )}
                {e.domain && (
                  <p className="mt-1 text-xs text-slate-500">domain {e.domain}</p>
                )}
              </li>
            ))}
            {entries.data.length === 0 && (
              <li className="py-3 text-sm text-muted-foreground">No directory entries yet.</li>
            )}
          </ul>
        )}
      </section>
    </div>
  );
}
