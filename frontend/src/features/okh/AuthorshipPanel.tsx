import { useQuery } from "@tanstack/react-query";
import { getOkhProvenance, type RecordProvenance } from "../../api/ohm/okh";
import { getOkwProvenance } from "../../api/ohm/okw";
import type { components } from "../../api/generated/schema";

type Credit = components["schemas"]["Credit"];

function creditLabel(c: Credit): string {
  return c.subject_did ?? c.external_id ?? "unknown";
}

function ProvenanceBody({ data }: { data: RecordProvenance }) {
  const authors = data.authored_by ?? [];
  return (
    <dl className="space-y-3">
      {authors.length > 0 && (
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Authored by
          </dt>
          <dd className="mt-1 space-y-1">
            {authors.map((c, i) => (
              <p key={i} className="break-all font-mono text-xs text-foreground">
                {creditLabel(c)}
                {c.role ? ` (${c.role})` : ""}
              </p>
            ))}
          </dd>
        </div>
      )}
      {data.published_by && (
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Published by
          </dt>
          <dd className="mt-1 break-all font-mono text-xs">{data.published_by}</dd>
        </div>
      )}
      {data.on_behalf_of && (
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            On behalf of
          </dt>
          <dd className="mt-1 break-all font-mono text-xs">{data.on_behalf_of}</dd>
        </div>
      )}
      {!authors.length && !data.published_by && !data.on_behalf_of && (
        <p className="text-sm text-muted-foreground">Empty provenance record.</p>
      )}
    </dl>
  );
}

export function AuthorshipPanel({
  kind,
  id,
}: {
  kind: "okh" | "okw";
  id: string;
}) {
  const query = useQuery({
    queryKey: [kind, "provenance", id],
    queryFn: () => (kind === "okh" ? getOkhProvenance(id) : getOkwProvenance(id)),
    retry: false,
  });

  return (
    <section
      aria-labelledby={`${kind}-authorship-heading`}
      className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
    >
      <h2
        id={`${kind}-authorship-heading`}
        className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
      >
        Authorship
      </h2>
      {query.isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
      {query.isError && (
        <p className="text-sm text-red-600 dark:text-red-400">
          {query.error instanceof Error ? query.error.message : "Failed to load provenance."}
        </p>
      )}
      {query.isSuccess && !query.data && (
        <p className="text-sm text-muted-foreground">No provenance recorded.</p>
      )}
      {query.data && <ProvenanceBody data={query.data} />}
    </section>
  );
}
