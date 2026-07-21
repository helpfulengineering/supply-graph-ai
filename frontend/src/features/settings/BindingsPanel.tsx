import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  bindOAuth,
  listBindings,
  startDomainBinding,
  verifyDomainBinding,
  type DomainBindStartResponse,
  type IdentityBinding,
} from "../../api/ohm/identity";
import { ApiError } from "../../api/ohm/client";
import { Badge } from "../../components/ui/Badge";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useAuth } from "../../context/AuthContext";

function copyText(text: string) {
  void navigator.clipboard.writeText(text);
}

export function BindingsPanel() {
  const queryClient = useQueryClient();
  const { reportAuthFailure } = useAuth();

  const [domainDid, setDomainDid] = useState("");
  const [domain, setDomain] = useState("");
  const [pending, setPending] = useState<DomainBindStartResponse | null>(null);

  const [oauthDid, setOauthDid] = useState("");
  const [provider, setProvider] = useState("github");
  const [externalSubject, setExternalSubject] = useState("");

  const bindings = useQuery({
    queryKey: ["identity", "bindings"],
    queryFn: () => listBindings(),
  });

  const start = useMutation({
    mutationFn: () => startDomainBinding(domainDid.trim(), domain.trim()),
    onSuccess: (res) => {
      setPending(res);
      void queryClient.invalidateQueries({ queryKey: ["identity", "bindings"] });
    },
    onError: reportAuthFailure,
  });

  const verify = useMutation({
    mutationFn: () =>
      verifyDomainBinding(
        pending?.binding.subject_did ?? domainDid.trim(),
        domain.trim(),
      ),
    onSuccess: () => {
      setPending(null);
      void queryClient.invalidateQueries({ queryKey: ["identity", "bindings"] });
      void queryClient.invalidateQueries({ queryKey: ["identity", "directory"] });
    },
    onError: reportAuthFailure,
  });

  const oauth = useMutation({
    mutationFn: () =>
      bindOAuth({
        subject_did: oauthDid.trim(),
        provider: provider.trim(),
        external_subject: externalSubject.trim(),
      }),
    onSuccess: () => {
      setExternalSubject("");
      void queryClient.invalidateQueries({ queryKey: ["identity", "bindings"] });
    },
    onError: reportAuthFailure,
  });

  return (
    <div className="space-y-8">
      <section
        aria-labelledby="domain-bind-heading"
        className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <h2 id="domain-bind-heading" className="text-lg font-semibold text-foreground">
          Domain bind
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Host a challenge at <code className="text-xs">.well-known/ohm-did.json</code>, then
          verify.
        </p>
        <form
          className="mt-4 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (domainDid.trim() && domain.trim()) start.mutate();
          }}
        >
          <label className="block text-sm font-medium">
            Subject DID
            <input
              value={domainDid}
              onChange={(e) => setDomainDid(e.target.value)}
              className="mt-1 w-full max-w-xl rounded-md border border-slate-300 px-3 py-2 font-mono text-sm dark:border-slate-600 dark:bg-slate-950"
              required
            />
          </label>
          <label className="block text-sm font-medium">
            Domain
            <input
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="example.org"
              className="mt-1 w-full max-w-md rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
              required
            />
          </label>
          <button
            type="submit"
            disabled={start.isPending || !domainDid.trim() || !domain.trim()}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {start.isPending ? "Starting…" : "Start"}
          </button>
          {start.isError && (
            <p className="text-sm text-red-600" role="alert">
              {start.error instanceof Error ? start.error.message : "Start failed"}
            </p>
          )}
        </form>

        {pending && (
          <div className="mt-5 space-y-3 border-t border-slate-100 pt-4 dark:border-slate-800">
            <p className="text-sm font-medium text-foreground">Host this document</p>
            <div className="flex flex-wrap items-center gap-2">
              <code className="break-all text-xs text-slate-600 dark:text-slate-300">
                {pending.well_known_url}
              </code>
              <button
                type="button"
                className="rounded-md border border-slate-300 px-2 py-1 text-xs dark:border-slate-600"
                onClick={() => copyText(pending.well_known_url)}
              >
                Copy URL
              </button>
            </div>
            <pre className="overflow-x-auto rounded-md bg-slate-50 p-3 text-xs dark:bg-slate-950">
              {JSON.stringify(pending.well_known_document, null, 2)}
            </pre>
            <button
              type="button"
              className="rounded-md border border-slate-300 px-2 py-1 text-xs dark:border-slate-600"
              onClick={() =>
                copyText(JSON.stringify(pending.well_known_document, null, 2))
              }
            >
              Copy JSON
            </button>
            <div>
              <button
                type="button"
                disabled={verify.isPending}
                className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
                onClick={() => verify.mutate()}
              >
                {verify.isPending ? "Verifying…" : "Verify"}
              </button>
              {verify.isError && (
                <p className="mt-2 text-sm text-red-600" role="alert">
                  {verifyErrorMessage(verify.error)}
                </p>
              )}
              {verify.isSuccess && (
                <p className="mt-2 text-sm text-green-700 dark:text-green-300" role="status">
                  Domain bound ({verify.data.external_id})
                </p>
              )}
            </div>
          </div>
        )}
      </section>

      <section
        aria-labelledby="oauth-bind-heading"
        className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <h2 id="oauth-bind-heading" className="text-lg font-semibold text-foreground">
          OAuth binding (record only)
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Store an external IdP subject after out-of-band verification. No redirect or callback.
        </p>
        <form
          className="mt-4 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (oauthDid.trim() && provider.trim() && externalSubject.trim()) {
              oauth.mutate();
            }
          }}
        >
          <label className="block text-sm font-medium">
            Subject DID
            <input
              value={oauthDid}
              onChange={(e) => setOauthDid(e.target.value)}
              className="mt-1 w-full max-w-xl rounded-md border border-slate-300 px-3 py-2 font-mono text-sm dark:border-slate-600 dark:bg-slate-950"
              required
            />
          </label>
          <label className="block text-sm font-medium">
            Provider
            <input
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              placeholder="github"
              className="mt-1 w-full max-w-xs rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
              required
            />
          </label>
          <label className="block text-sm font-medium">
            External subject
            <input
              value={externalSubject}
              onChange={(e) => setExternalSubject(e.target.value)}
              placeholder="username or IdP subject id"
              className="mt-1 w-full max-w-md rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
              required
            />
          </label>
          <button
            type="submit"
            disabled={
              oauth.isPending ||
              !oauthDid.trim() ||
              !provider.trim() ||
              !externalSubject.trim()
            }
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            Record binding
          </button>
          {oauth.isError && (
            <p className="text-sm text-red-600" role="alert">
              {oauth.error instanceof Error ? oauth.error.message : "OAuth bind failed"}
            </p>
          )}
          {oauth.isSuccess && (
            <p className="text-sm text-green-700 dark:text-green-300" role="status">
              Recorded {oauth.data.external_id}
            </p>
          )}
        </form>
      </section>

      <section
        aria-labelledby="bindings-list-heading"
        className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <h2 id="bindings-list-heading" className="text-lg font-semibold text-foreground">
          Bindings
        </h2>
        {bindings.isLoading && <LoadingSpinner message="Loading bindings…" />}
        {bindings.isError && (
          <p className="mt-3 text-sm text-red-600" role="alert">
            {bindings.error.message}
          </p>
        )}
        {bindings.data && <BindingsList items={bindings.data} />}
      </section>
    </div>
  );
}

function BindingsList({ items }: { items: IdentityBinding[] }) {
  if (items.length === 0) {
    return <p className="mt-3 text-sm text-muted-foreground">No bindings yet.</p>;
  }
  return (
    <ul className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
      {items.map((b) => (
        <li key={b.binding_id} className="py-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="blue">{b.kind}</Badge>
            {b.verified ? (
              <Badge variant="green">verified</Badge>
            ) : (
              <Badge variant="default">pending</Badge>
            )}
          </div>
          <p className="mt-1 break-all font-mono text-xs text-foreground">{b.external_id}</p>
          <p className="mt-0.5 break-all font-mono text-xs text-slate-500">{b.subject_did}</p>
        </li>
      ))}
    </ul>
  );
}

function verifyErrorMessage(err: unknown): string {
  if (!(err instanceof ApiError)) {
    return err instanceof Error ? err.message : "Verify failed";
  }
  const msg = err.message.toLowerCase();
  if (msg.includes("challenge") || msg.includes("mismatch")) {
    return "Challenge mismatch — re-host the well-known document and try again.";
  }
  if (msg.includes("fetch") || msg.includes("connect") || err.status === 502) {
    return "Fetch failed — could not retrieve .well-known/ohm-did.json.";
  }
  return err.message;
}
