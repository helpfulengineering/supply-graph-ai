"use client";

import Link from "next/link";
import { PageHero } from "../components/layout/PageHero";
import { usePathname } from "next/navigation";
import { SessionPanel } from "../features/settings/SessionPanel";
import { DomainPanel } from "../features/settings/DomainPanel";
import { KeysAccountsPanel } from "../features/settings/KeysAccountsPanel";
import { IdentitiesPanel } from "../features/settings/IdentitiesPanel";
import { GrantsPanel } from "../features/settings/GrantsPanel";
import { SpacesPanel } from "../features/settings/SpacesPanel";
import { ReputationPanel } from "../features/settings/ReputationPanel";
import { BindingsPanel } from "../features/settings/BindingsPanel";
import { DirectoryPanel } from "../features/settings/DirectoryPanel";
import { FederationPanel } from "../features/settings/FederationPanel";
import { LLMCredentialsPanel } from "../features/settings/LLMCredentialsPanel";
import { MatchingRulesPanel } from "../features/settings/MatchingRulesPanel";
import { InventoryPanel } from "../features/settings/InventoryPanel";
import { StoragePanel } from "../features/settings/StoragePanel";
import { SecurityPolicyBadge } from "../features/settings/SecurityPolicyBadge";
import { useAuth } from "../context/AuthContext";
import { SECTION_LABEL_SM } from "../components/ui/typography";
import { cn } from "@/lib/utils";

type Tab = { to: string; label: string };

const accessTabs: Tab[] = [
  { to: "/settings/session", label: "Session" },
  { to: "/settings/domain", label: "Domain" },
];

const nodeTabs: Tab[] = [
  { to: "/settings/storage", label: "Storage" },
  { to: "/settings/llm", label: "LLM providers" },
  { to: "/settings/matching", label: "Matching rules" },
  { to: "/settings/inventory", label: "Inventory" },
  { to: "/settings/federation", label: "Federation" },
];

const identityTabs: Tab[] = [
  { to: "/settings/keys", label: "Keys & accounts" },
  { to: "/settings/identities", label: "Identities" },
  { to: "/settings/grants", label: "Grants" },
  { to: "/settings/spaces", label: "Spaces" },
  { to: "/settings/bindings", label: "Bindings" },
  { to: "/settings/directory", label: "Directory" },
  { to: "/settings/reputation", label: "Reputation" },
];

type TabGroup = { label: string; tabs: Tab[] };

function panelFor(pathname: string) {
  if (pathname.includes("/domain")) return <DomainPanel />;
  if (pathname.includes("/inventory")) return <InventoryPanel />;
  if (pathname.includes("/keys")) return <KeysAccountsPanel />;
  if (pathname.includes("/storage")) return <StoragePanel />;
  if (pathname.includes("/llm")) return <LLMCredentialsPanel />;
  if (pathname.includes("/matching")) return <MatchingRulesPanel />;
  if (pathname.includes("/identities")) return <IdentitiesPanel />;
  if (pathname.includes("/grants")) return <GrantsPanel />;
  if (pathname.includes("/spaces")) return <SpacesPanel />;
  if (pathname.includes("/bindings")) return <BindingsPanel />;
  if (pathname.includes("/directory")) return <DirectoryPanel />;
  if (pathname.includes("/federation")) return <FederationPanel />;
  if (pathname.includes("/reputation")) return <ReputationPanel />;
  return <SessionPanel />;
}

function TabStrip({
  groups,
  pathname,
}: {
  groups: TabGroup[];
  pathname: string;
}) {
  return (
    <nav className="space-y-3" aria-label="Settings">
      {groups.map((group) => (
        <div key={group.label}>
          <p className={cn(SECTION_LABEL_SM, "px-3")}>{group.label}</p>
          <div
            className="mt-1 flex flex-wrap gap-1 border-b border-border"
            role="group"
            aria-label={group.label}
          >
            {group.tabs.map(({ to, label }) => {
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
          </div>
        </div>
      ))}
    </nav>
  );
}

export function SettingsPage() {
  const pathname = usePathname() ?? "";
  const { isAdmin } = useAuth();
  const groups: TabGroup[] = isAdmin
    ? [
        { label: "Access", tabs: accessTabs },
        { label: "Node", tabs: nodeTabs },
        { label: "Identity", tabs: identityTabs },
      ]
    : [{ label: "Access", tabs: accessTabs }];

  return (
    <div className="space-y-6">
      <div>
        {/* Terms rather than a string, but still no hrefs — and that is the
            decision, not an omission. These three names are the tab bar
            immediately below, so linking them puts two links to
            /settings/identities on the page under the same name: a duplicate
            control for a pointer and a second identical stop for a screen
            reader. A crumb links where it is the only way to somewhere.

            Written as terms so that stays legible. As a string it was
            indistinguishable from the pages that simply had not been migrated
            yet, and the audit could not tell the two apart. */}
        <PageHero
          title="Settings"
          description="Configure this node and its credentials."
          crumb={[
            { label: "session" },
            { label: "keys" },
            { label: "identities" },
          ]}
        />
      </div>

      <TabStrip groups={groups} pathname={pathname} />

      {panelFor(pathname)}

      <footer className="border-t border-border pt-4">
        <p className={cn(SECTION_LABEL_SM, "mb-2")}>Security policy</p>
        <SecurityPolicyBadge />
      </footer>
    </div>
  );
}
