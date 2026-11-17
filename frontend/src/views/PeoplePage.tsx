"use client";

import Link from "next/link";
import { PageHero } from "../components/layout/PageHero";
import { usePathname } from "next/navigation";
import { InvitesPanel } from "../features/settings/InvitesPanel";
import { MembersPanel } from "../features/settings/MembersPanel";
import { OrganisationsPanel } from "../features/settings/OrganisationsPanel";
import { useAuth } from "../context/AuthContext";

const peopleTabs = [
  { to: "/people/invites", label: "Invites", needsCoordinate: true },
  { to: "/people/members", label: "Members", needsCoordinate: true },
  { to: "/people/organisations", label: "Organisations", needsCoordinate: false },
] as const;

function panelFor(pathname: string) {
  if (pathname.includes("/invites")) return <InvitesPanel />;
  if (pathname.includes("/members")) return <MembersPanel />;
  return <OrganisationsPanel />;
}

/**
 * Who may join, who is here, and which organisations you administer.
 *
 * Promoted out of Settings so coordinators and org admins find these without
 * opening the instance-administration strip. Invites and Members need
 * coordinate (or admin); Organisations is available to anyone signed in.
 */
export function PeoplePage() {
  const pathname = usePathname() ?? "";
  const { isAdmin, isCoordinator, signedIn } = useAuth();
  const canCoordinate = isAdmin || isCoordinator;
  const tabs = peopleTabs.filter(
    (tab) =>
      (!tab.needsCoordinate || canCoordinate) &&
      (tab.needsCoordinate || signedIn || canCoordinate),
  );

  return (
    <div className="space-y-6">
      <PageHero
        title="People"
        description="Who may join, who is here, and which organisations you administer."
        crumb={[
          { label: "invites" },
          { label: "members" },
          { label: "organisations" },
        ]}
      />

      <nav
        className="flex flex-wrap gap-1 border-b border-border"
        aria-label="People"
      >
        {tabs.map(({ to, label }) => {
          const isActive = pathname === to;
          return (
            <Link
              key={to}
              href={to}
              aria-current={isActive ? "page" : undefined}
              className={[
                "border-b-2 px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "border-primary/30 text-primary-ink"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              ].join(" ")}
            >
              {label}
            </Link>
          );
        })}
      </nav>

      {panelFor(pathname)}
    </div>
  );
}
