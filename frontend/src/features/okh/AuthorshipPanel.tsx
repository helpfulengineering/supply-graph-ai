import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getOkhProvenance,
  setOkhAttribution,
  type RecordProvenance,
} from "../../api/ohm/okh";
import { getOkwProvenance, setOkwAttribution } from "../../api/ohm/okw";
import { listAffiliations } from "../../api/ohm/identity";
import type { components } from "../../api/generated/schema";
import { Button } from "../../components/ui/button";
import { FIELD, LABEL } from "../../components/ui/field";
import { PANEL } from "../../components/ui/surface";
import {
  SECTION_LABEL,
  SECTION_LABEL_SM,
} from "../../components/ui/typography";
import { useAuth } from "../../context/AuthContext";
import { cn } from "@/lib/utils";

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
          <dt className={SECTION_LABEL_SM}>Authored by</dt>
          <dd className="mt-1 space-y-1">
            {authors.map((c, i) => (
              <p
                key={i}
                className="break-all font-mono text-xs text-foreground"
              >
                {creditLabel(c)}
                {c.role ? ` (${c.role})` : ""}
              </p>
            ))}
          </dd>
        </div>
      )}
      {data.published_by && (
        <div>
          <dt className={SECTION_LABEL_SM}>Published by</dt>
          <dd className="mt-1 break-all font-mono text-xs">
            {data.published_by}
          </dd>
        </div>
      )}
      {data.on_behalf_of && (
        <div>
          <dt className={SECTION_LABEL_SM}>On behalf of</dt>
          <dd className="mt-1">
            <span className="break-all font-mono text-xs">
              {data.on_behalf_of}
            </span>
            <span className="mt-1 block text-xs text-muted-foreground">
              {data.organisation_verified
                ? "Verified"
                : "Unverified — this node could not check"}
            </span>
          </dd>
        </div>
      )}
      {!authors.length && !data.published_by && !data.on_behalf_of && (
        <p className="text-sm text-muted-foreground">
          Empty provenance record.
        </p>
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
    queryFn: () =>
      kind === "okh" ? getOkhProvenance(id) : getOkwProvenance(id),
    retry: false,
  });

  return (
    <section aria-labelledby={`${kind}-authorship-heading`} className={PANEL}>
      <h2
        id={`${kind}-authorship-heading`}
        className={cn(SECTION_LABEL, "mb-3")}
      >
        Authorship
      </h2>
      {query.isLoading && (
        <p className="text-sm text-muted-foreground">Loading…</p>
      )}
      {query.isError && (
        <p className="text-sm text-destructive">
          {query.error instanceof Error
            ? query.error.message
            : "Failed to load provenance."}
        </p>
      )}
      {query.isSuccess && !query.data && (
        <p className="text-sm text-muted-foreground">No provenance recorded.</p>
      )}
      {query.data && <ProvenanceBody data={query.data} />}
      <AttributeRecord kind={kind} id={id} />
    </section>
  );
}

function AttributeRecord({ kind, id }: { kind: "okh" | "okw"; id: string }) {
  const { signedIn, reportAuthFailure } = useAuth();
  const queryClient = useQueryClient();
  const [choice, setChoice] = useState("");
  const affiliations = useQuery({
    queryKey: ["identity", "affiliations"],
    queryFn: listAffiliations,
    enabled: signedIn,
  });
  const save = useMutation({
    mutationFn: (onBehalfOf: string | null) =>
      kind === "okh"
        ? setOkhAttribution(id, onBehalfOf)
        : setOkwAttribution(id, onBehalfOf),
    onSuccess: () => {
      setChoice("");
      void queryClient.invalidateQueries({
        queryKey: [kind, "provenance", id],
      });
    },
    onError: reportAuthFailure,
  });
  if (!signedIn || !affiliations.data) return null;
  const org = choice === "none" ? null : choice;

  return (
    <form
      className="mt-4 flex flex-wrap items-end gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (choice) save.mutate(org);
      }}
    >
      <label className={LABEL}>
        <span className="sr-only">Organisation</span>
        <select
          value={choice}
          onChange={(e) => setChoice(e.target.value)}
          className={`${FIELD} mt-1`}
        >
          <option value="">Attribute to…</option>
          {affiliations.data.map((row) => (
            <option key={row.space_did} value={row.space_did}>
              {row.display_name}
            </option>
          ))}
          <option value="none">Remove organisation</option>
        </select>
      </label>
      <Button type="submit" disabled={!choice || save.isPending}>
        {choice === "none" ? "Remove" : "Attribute"}
      </Button>
    </form>
  );
}
