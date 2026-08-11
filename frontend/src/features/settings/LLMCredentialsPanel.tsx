import { useState } from "react";
import { FIELD, FIELD_MONO, FIELD_SM, LABEL } from "../../components/ui/field";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  deleteLLMCredential,
  listLLMCredentials,
  testLLMCredential,
  upsertLLMCredential,
} from "../../api/ohm/llm";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useAuth } from "../../context/AuthContext";

const PROVIDERS = [
  "anthropic",
  "openai",
  "azure_openai",
  "aws_bedrock",
  "google",
  "local",
] as const;

export function LLMCredentialsPanel() {
  const queryClient = useQueryClient();
  const { reportAuthFailure } = useAuth();
  const [provider, setProvider] = useState<string>("anthropic");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const credentials = useQuery({
    queryKey: ["llm", "credentials"],
    queryFn: listLLMCredentials,
    retry: false,
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["llm", "credentials"] });
  };

  const upsert = useMutation({
    mutationFn: () =>
      upsertLLMCredential(provider, {
        api_key: apiKey.trim(),
        model: model.trim() || null,
        activate: true,
      }),
    onSuccess: (status) => {
      setApiKey("");
      setMessage(
        `Saved ${status.provider} (${status.masked_key}) and activated.`,
      );
      invalidate();
    },
    onError: (err) => {
      reportAuthFailure(err);
      setMessage(
        err instanceof Error ? err.message : "Failed to save credential",
      );
    },
  });

  const remove = useMutation({
    mutationFn: (name: string) => deleteLLMCredential(name),
    onSuccess: () => {
      setMessage("Credential deleted.");
      invalidate();
    },
    onError: reportAuthFailure,
  });

  const test = useMutation({
    mutationFn: (name: string) => testLLMCredential(name),
    onSuccess: () => setMessage("Health check passed."),
    onError: (err) => {
      reportAuthFailure(err);
      setMessage(err instanceof Error ? err.message : "Health check failed");
    },
  });

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Store an encrypted provider API key on this node and hot-swap it into
        the running LLM service. Keys are never shown in full after save — only
        a masked suffix. Requires{" "}
        <code className="text-xs">LLM_ENCRYPTION_KEY</code> or non-default{" "}
        <code className="text-xs">LLM_ENCRYPTION_SALT</code> /{" "}
        <code className="text-xs">LLM_ENCRYPTION_PASSWORD</code>.
      </p>

      {message && (
        <p
          className="rounded-md border border-border bg-background p-3 text-sm"
          role="status"
        >
          {message}
        </p>
      )}

      <section
        aria-labelledby="llm-credentials-form-heading"
        className="rounded-xl border border-border bg-card p-5"
      >
        <h2
          id="llm-credentials-form-heading"
          className="text-lg font-semibold text-foreground"
        >
          Set provider key
        </h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className={LABEL}>
            <span className="font-medium text-foreground">Provider</span>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className={`${FIELD} mt-1 w-full`}
            >
              {PROVIDERS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
          <label className={LABEL}>
            <span className="font-medium text-foreground">
              Model (optional)
            </span>
            <input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="claude-sonnet-4-5-20250929"
              className={`${FIELD} mt-1 w-full`}
            />
          </label>
          <label className="block text-sm sm:col-span-2">
            <span className="font-medium text-foreground">API key</span>
            <input
              type="password"
              autoComplete="off"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className={`${FIELD_MONO} mt-1 w-full`}
            />
          </label>
        </div>
        <button
          type="button"
          disabled={!apiKey.trim() || upsert.isPending}
          onClick={() => upsert.mutate()}
          className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-on-accent hover:bg-primary disabled:opacity-60"
        >
          {upsert.isPending ? "Saving…" : "Save and activate"}
        </button>
      </section>

      <section
        aria-labelledby="llm-credentials-list-heading"
        className="rounded-xl border border-border bg-card p-5"
      >
        <h2
          id="llm-credentials-list-heading"
          className="text-lg font-semibold text-foreground"
        >
          Stored credentials
        </h2>
        {credentials.isLoading && (
          <LoadingSpinner message="Loading credentials…" />
        )}
        {credentials.isError && (
          <p className="mt-3 text-sm text-destructive" role="alert">
            {credentials.error.message}
          </p>
        )}
        {credentials.data && credentials.data.length === 0 && (
          <p className="mt-3 text-sm text-muted-foreground">
            No credentials stored yet.
          </p>
        )}
        {credentials.data && credentials.data.length > 0 && (
          <ul className="mt-4 divide-y divide-border">
            {credentials.data.map((c) => (
              <li
                key={c.provider}
                className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm"
              >
                <div>
                  <p className="font-medium text-foreground">{c.provider}</p>
                  <p className="font-mono text-xs text-muted-foreground">
                    {c.masked_key}
                    {c.model ? ` · ${c.model}` : ""}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => test.mutate(c.provider)}
                    disabled={test.isPending}
                    className={FIELD_SM}
                  >
                    Test
                  </button>
                  <button
                    type="button"
                    onClick={() => remove.mutate(c.provider)}
                    disabled={remove.isPending}
                    className={`${FIELD_SM} border-destructive text-destructive`}
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
