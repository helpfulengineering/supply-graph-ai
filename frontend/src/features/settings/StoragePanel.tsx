import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FIELD, FIELD_MONO, LABEL } from "../../components/ui/field";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { Badge } from "../../components/ui/Badge";
import { useAuth } from "../../context/AuthContext";
import { PANEL, PANEL_INSET } from "../../components/ui/surface";
import {
  SECTION_LABEL_SM,
  SECTION_TITLE,
} from "../../components/ui/typography";
import { cn } from "@/lib/utils";
import {
  configureStorage,
  fetchStorageConfig,
  STORAGE_PROVIDERS,
  STORAGE_PROVIDER_LABELS,
  type StorageConfigureData,
  type StorageProvider,
} from "../../api/ohm/storage";

/** Where the reported configuration came from, in words rather than a token. */
const SOURCE_LABELS: Record<string, string> = {
  live: "the running service",
  persisted: "the saved configuration",
  environment: "environment variables",
  none: "nowhere — storage is unconfigured",
};

export function StoragePanel() {
  const queryClient = useQueryClient();
  const { reportAuthFailure } = useAuth();

  const [provider, setProvider] = useState<StorageProvider>("local");
  const [bucket, setBucket] = useState("");
  const [region, setRegion] = useState("");
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [result, setResult] = useState<StorageConfigureData | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  const current = useQuery({
    queryKey: ["storage", "config"],
    queryFn: fetchStorageConfig,
    retry: false,
  });

  const apply = useMutation({
    mutationFn: () =>
      configureStorage({
        provider,
        bucket: bucket.trim(),
        region: region.trim() || null,
        endpoint_url: null,
        // Blank fields are dropped rather than sent empty: the server checks
        // credential names against the provider, and an empty string is not a
        // credential.
        credentials: Object.fromEntries(
          Object.entries(credentials).filter(([, v]) => v.trim()),
        ),
      }),
    onSuccess: (data) => {
      setResult(data);
      setFailure(null);
      setCredentials({});
      void queryClient.invalidateQueries({ queryKey: ["storage", "config"] });
    },
    onError: (err) => {
      reportAuthFailure(err);
      setResult(null);
      // Shown as the server wrote it. The server is the only layer that knows
      // the instance is still serving from its previous configuration, and
      // that is the most useful half of the message.
      setFailure(
        err instanceof Error
          ? err.message
          : "Failed to change storage configuration",
      );
    },
  });

  const credentialFields = STORAGE_PROVIDERS[provider];
  const config = current.data?.config;
  const fingerprint = current.data?.fingerprint;

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Point this instance at a different storage backend. The new backend is
        checked end to end — connect, write, read back, then validate or create
        the directory structure — before anything changes. If the check fails,
        the instance keeps serving from its current configuration.
      </p>

      <section aria-labelledby="storage-current-heading" className={PANEL}>
        <h2 id="storage-current-heading" className={SECTION_TITLE}>
          Current configuration
        </h2>

        {current.isLoading && (
          <LoadingSpinner message="Loading storage configuration…" />
        )}

        {current.isError && (
          <p className="mt-3 text-sm text-destructive" role="alert">
            {current.error.message}
          </p>
        )}

        {config && (
          <>
            <dl className="mt-3 space-y-2 text-sm">
              <div>
                <dt className={SECTION_LABEL_SM}>Provider</dt>
                <dd className="text-foreground">
                  {STORAGE_PROVIDER_LABELS[
                    config.provider as StorageProvider
                  ] ?? config.provider}
                </dd>
              </div>
              <div>
                <dt className={SECTION_LABEL_SM}>Bucket or path</dt>
                <dd className="break-all font-mono text-xs text-foreground">
                  {config.bucket || "—"}
                </dd>
              </div>
              {config.region && (
                <div>
                  <dt className={SECTION_LABEL_SM}>Region</dt>
                  <dd className="text-foreground">{config.region}</dd>
                </div>
              )}
              <div>
                <dt className={cn(SECTION_LABEL_SM, "mb-1.5")}>
                  Credentials set
                </dt>
                <dd className="flex flex-wrap gap-1.5">
                  {config.credential_names.length === 0 ? (
                    <span className="text-sm text-muted-foreground">None</span>
                  ) : (
                    config.credential_names.map((name) => (
                      <Badge key={name} variant="blue">
                        {name}
                      </Badge>
                    ))
                  )}
                </dd>
              </div>
              <div>
                <dt className={SECTION_LABEL_SM}>Read from</dt>
                <dd className="text-foreground">
                  {SOURCE_LABELS[config.source] ?? config.source}
                  {config.persisted ? "" : " — not yet saved to disk"}
                </dd>
              </div>
            </dl>

            {!config.configured && (
              <p className={cn(PANEL_INSET, "mt-3 text-sm")} role="status">
                Storage is configured but not connected. The app starts in this
                state rather than refusing to boot, so reads and writes will
                fail until the backend is reachable.
              </p>
            )}
          </>
        )}

        {fingerprint && (
          <div className="mt-4 border-t border-border pt-3">
            <p className={SECTION_LABEL_SM}>What answered</p>
            {fingerprint.error ? (
              <p className="mt-1 text-sm text-destructive">
                {fingerprint.error}
              </p>
            ) : (
              <p className="mt-1 text-sm text-muted-foreground">
                {fingerprint.container ?? "—"} · {fingerprint.okh_count ?? "?"}{" "}
                designs, {fingerprint.okw_count ?? "?"} facilities
              </p>
            )}
          </div>
        )}
      </section>

      <section aria-labelledby="storage-change-heading" className={PANEL}>
        <h2 id="storage-change-heading" className={SECTION_TITLE}>
          Change backend
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Existing data stays where it is. This changes which backend is read
          and written, it does not move anything.
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className={LABEL}>
            <span className="font-medium text-foreground">Provider</span>
            <select
              value={provider}
              onChange={(e) => {
                setProvider(e.target.value as StorageProvider);
                // Credential names are per-provider; carrying them across
                // would submit fields the new provider rejects.
                setCredentials({});
              }}
              className={`${FIELD} mt-1 w-full`}
            >
              {(Object.keys(STORAGE_PROVIDERS) as StorageProvider[]).map(
                (p) => (
                  <option key={p} value={p}>
                    {STORAGE_PROVIDER_LABELS[p]}
                  </option>
                ),
              )}
            </select>
          </label>

          <label className={LABEL}>
            <span className="font-medium text-foreground">
              {provider === "local" ? "Path" : "Bucket or container"}
            </span>
            <input
              value={bucket}
              onChange={(e) => setBucket(e.target.value)}
              placeholder={provider === "local" ? "~/ohm-data" : "my-container"}
              className={`${FIELD} mt-1 w-full`}
            />
          </label>

          {provider !== "local" && (
            <label className={LABEL}>
              <span className="font-medium text-foreground">
                Region (optional)
              </span>
              <input
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                className={`${FIELD} mt-1 w-full`}
              />
            </label>
          )}

          {credentialFields.map((name) => (
            <label key={name} className={LABEL}>
              <span className="font-medium text-foreground">{name}</span>
              <input
                type="password"
                autoComplete="off"
                value={credentials[name] ?? ""}
                onChange={(e) =>
                  setCredentials((prev) => ({
                    ...prev,
                    [name]: e.target.value,
                  }))
                }
                className={`${FIELD_MONO} mt-1 w-full`}
              />
            </label>
          ))}
        </div>

        {credentialFields.length > 0 && (
          <p className="mt-3 text-xs text-muted-foreground">
            Credentials are write-only: they can be set and replaced, never read
            back. Only which names are set is ever shown.
          </p>
        )}

        <button
          type="button"
          disabled={!bucket.trim() || apply.isPending}
          onClick={() => apply.mutate()}
          className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-on-accent hover:bg-primary disabled:opacity-60"
        >
          {apply.isPending ? "Checking backend…" : "Validate and switch"}
        </button>

        {failure && (
          <p className="mt-4 text-sm text-destructive" role="alert">
            {failure}
          </p>
        )}

        {result && (
          <div className={cn(PANEL_INSET, "mt-4 text-sm")} role="status">
            <p className="font-medium text-foreground">
              Now using{" "}
              {STORAGE_PROVIDER_LABELS[result.provider as StorageProvider] ??
                result.provider}
              : <span className="font-mono text-xs">{result.bucket}</span>
            </p>
            <p className="mt-1 text-muted-foreground">
              {result.prefixes_created.length > 0
                ? `Created ${result.prefixes_created.join(", ")}`
                : "Every prefix was already present — nothing to create."}
            </p>
            {result.prefixes_found.length > 0 &&
              result.prefixes_created.length > 0 && (
                <p className="text-muted-foreground">
                  Already present: {result.prefixes_found.join(", ")}
                </p>
              )}
            {result.previous_bucket && (
              <p className="mt-1 text-muted-foreground">
                Previously {result.previous_provider}: {result.previous_bucket}.
                Data left there is untouched.
              </p>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
