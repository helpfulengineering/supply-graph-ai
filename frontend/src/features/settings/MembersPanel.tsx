"use client";

import { useQuery } from "@tanstack/react-query";
import { listMembers } from "../../api/ohm/identity";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { PANEL } from "../../components/ui/surface";
import { SECTION_TITLE } from "../../components/ui/typography";

export function MembersPanel() {
  const members = useQuery({
    queryKey: ["identity", "members"],
    queryFn: listMembers,
  });

  if (members.isPending) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <section className={PANEL}>
      <h2 className={SECTION_TITLE}>Members</h2>
      <ul className="mt-3 space-y-3 text-sm">
        {(members.data ?? []).map((row) => (
          <li key={row.username ?? row.display_name}>
            <p>
              {row.display_name}
              {row.username ? ` (${row.username})` : ""}
            </p>
            <ul className="mt-1 space-y-1 text-muted-foreground">
              {row.facilities.map((facility) => (
                <li key={facility.name}>
                  {facility.name}
                  {facility.processes.length
                    ? ` — ${facility.processes.join(", ")}`
                    : ""}{" "}
                  <span>{facility.visibility}</span>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  );
}
