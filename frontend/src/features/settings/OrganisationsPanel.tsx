"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  affiliateMember,
  listAdministered,
  renewAffiliation,
  unaffiliateMember,
  type AdministeredOrganisation,
} from "../../api/ohm/identity";
import { FIELD, LABEL } from "../../components/ui/field";
import { Button } from "../../components/ui/button";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useAuth } from "../../context/AuthContext";
import { PANEL } from "../../components/ui/surface";
import { SECTION_TITLE } from "../../components/ui/typography";

function OrganisationSection({
  org,
}: {
  org: AdministeredOrganisation;
}) {
  const queryClient = useQueryClient();
  const { reportAuthFailure } = useAuth();
  const [subjectDid, setSubjectDid] = useState("");
  const refresh = () =>
    void queryClient.invalidateQueries({
      queryKey: ["identity", "affiliations", "administered"],
    });
  const affiliate = useMutation({
    mutationFn: () => affiliateMember(org.space_did, subjectDid.trim()),
    onSuccess: () => {
      setSubjectDid("");
      refresh();
    },
    onError: reportAuthFailure,
  });
  const renew = useMutation({
    mutationFn: renewAffiliation,
    onSuccess: refresh,
    onError: reportAuthFailure,
  });
  const unaffiliate = useMutation({
    mutationFn: unaffiliateMember,
    onSuccess: refresh,
    onError: reportAuthFailure,
  });

  return (
    <section className={PANEL}>
      <h2 className={SECTION_TITLE}>{org.display_name}</h2>
      <form
        className="mt-3 flex flex-wrap items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          affiliate.mutate();
        }}
      >
        <label className={LABEL}>
          Person
          <input
            value={subjectDid}
            onChange={(e) => setSubjectDid(e.target.value)}
            placeholder="did:key:…"
            className={`${FIELD} mt-1`}
          />
        </label>
        <Button type="submit" disabled={!subjectDid.trim() || affiliate.isPending}>
          Affiliate
        </Button>
      </form>
      <ul className="mt-4 space-y-2">
        {org.members.map((member) => (
          <li
            key={member.grant_id}
            className="flex flex-wrap items-center gap-2 text-sm"
          >
            <span>{member.display_name}</span>
            <span className="text-muted-foreground">
                  Expires {member.expires_at.slice(0, 10)}
            </span>
            <Button
              type="button"
              variant="outline"
              onClick={() => renew.mutate(member.grant_id)}
            >
              Renew
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => unaffiliate.mutate(member.grant_id)}
            >
              Unaffiliate
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function OrganisationsPanel() {
  const organisations = useQuery({
    queryKey: ["identity", "affiliations", "administered"],
    queryFn: listAdministered,
  });

  if (organisations.isLoading) return <LoadingSpinner />;
  if (organisations.isError) {
    return (
      <p className="text-sm text-destructive" role="alert">
        {organisations.error instanceof Error
          ? organisations.error.message
          : "Failed to load organisations."}
      </p>
    );
  }

  const rows = organisations.data ?? [];
  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        You do not administer an organisation.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {rows.map((org) => (
        <OrganisationSection key={org.space_did} org={org} />
      ))}
    </div>
  );
}
