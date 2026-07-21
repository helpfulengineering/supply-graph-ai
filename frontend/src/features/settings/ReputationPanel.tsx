import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listReputation } from "../../api/ohm/identity";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { AttestationList } from "../identity/AttestationList";

export function ReputationPanel() {
  const [input, setInput] = useState("");
  const [subjectDid, setSubjectDid] = useState("");

  const query = useQuery({
    queryKey: ["identity", "reputation", subjectDid],
    queryFn: () => listReputation(subjectDid),
    enabled: Boolean(subjectDid),
    retry: false,
  });

  return (
    <div className="space-y-6">
      <section
        aria-labelledby="reputation-heading"
        className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <h2 id="reputation-heading" className="text-lg font-semibold text-foreground">
          Reputation lookup
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Known-type, signature-valid attestations about a subject DID (no numeric score).
        </p>
        <form
          className="mt-4 flex flex-wrap items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            const did = input.trim();
            if (did) setSubjectDid(did);
          }}
        >
          <label className="block min-w-[16rem] flex-1 text-sm font-medium">
            Subject DID
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="did:key:…"
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm dark:border-slate-600 dark:bg-slate-950"
              required
            />
          </label>
          <button
            type="submit"
            disabled={!input.trim()}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            Look up
          </button>
        </form>

        {query.isLoading && <LoadingSpinner message="Loading reputation…" />}
        {query.isError && (
          <p className="mt-3 text-sm text-red-600" role="alert">
            {query.error instanceof Error ? query.error.message : "Lookup failed"}
          </p>
        )}
        {query.data && (
          <div className="mt-4">
            <AttestationList items={query.data} />
          </div>
        )}
      </section>
    </div>
  );
}
