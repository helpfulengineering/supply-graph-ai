"use client";

import Link from "next/link";
import { PageHero } from "../components/layout/PageHero";
import { usePathname } from "next/navigation";
import { SessionPanel } from "../features/settings/SessionPanel";
import { KeysAccountsPanel } from "../features/settings/KeysAccountsPanel";
import { IdentitiesPanel } from "../features/settings/IdentitiesPanel";
import { GrantsPanel } from "../features/settings/GrantsPanel";
import { SpacesPanel } from "../features/settings/SpacesPanel";
import { ReputationPanel } from "../features/settings/ReputationPanel";
import { BindingsPanel } from "../features/settings/BindingsPanel";
import { DirectoryPanel } from "../features/settings/DirectoryPanel";
import { FederationPanel } from "../features/settings/FederationPanel";
import { LLMCredentialsPanel } from "../features/settings/LLMCredentialsPanel";
import { SecurityPolicyBadge } from "../features/settings/SecurityPolicyBadge";
import { useAuth } from "../context/AuthContext";
import { SECTION_LABEL_SM } from "../components/ui/typography";
import { cn } from "@/lib/utils";

const sessionTab = { to: "/settings/session", label: "Session" } as const;

const adminTabs = [
  { to: "/settings/keys", label: "Keys & accounts" },
  { to: "/settings/llm", label: "LLM providers" },
  { to: "/settings/identities", label: "Identities" },
  { to: "/settings/grants", label: "Grants" },
  { to: "/settings/spaces", label: "Spaces" },
  { to: "/settings/bindings", label: "Bindings" },
  { to: "/settings/directory", label: "Directory" },
  { to: "/settings/federation", label: "Federation" },
  { to: "/settings/reputation", label: "Reputation" },
] as const;

function panelFor(pathname: string) {
  if (pathname.includes("/keys")) return <KeysAccountsPanel />;
  if (pathname.includes("/llm")) return <LLMCredentialsPanel />;
  if (pathname.includes("/identities")) return <IdentitiesPanel />;
  if (pathname.includes("/grants")) return <GrantsPanel />;
  if (pathname.includes("/spaces")) return <SpacesPanel />;
  if (pathname.includes("/bindings")) return <BindingsPanel />;
  if (pathname.includes("/directory")) return <DirectoryPanel />;
  if (pathname.includes("/federation")) return <FederationPanel />;
  if (pathname.includes("/reputation")) return <ReputationPanel />;
  return <SessionPanel />;
}

export function SettingsPage() {
  const pathname = usePathname() ?? "";
  const { isAdmin } = useAuth();
  const tabs = isAdmin ? [sessionTab, ...adminTabs] : [sessionTab];

  return (
    <div className="space-y-6">
      <div>
        {/* Left as text on purpose. These three terms are the tab bar
            immediately below, so linking them puts two links to
            /settings/identities on the page under the same name — a duplicate
            control for a pointer and a second identical stop for a screen
            reader. A crumb links where it is the only way to somewhere. */}
        <PageHero title="Settings" crumb="session · keys · identities" />
      </div>

      <nav
        className="flex flex-wrap gap-1 border-b border-border"
        aria-label="Settings"
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

      <footer className="border-t border-border pt-4">
        <p className={cn(SECTION_LABEL_SM, "mb-2")}>Security policy</p>
        <SecurityPolicyBadge />
      </footer>
    </div>
  );
}
