import { NavLink, useLocation } from "react-router-dom";
import { SessionPanel } from "../features/settings/SessionPanel";
import { KeysAccountsPanel } from "../features/settings/KeysAccountsPanel";
import { IdentitiesPanel } from "../features/settings/IdentitiesPanel";
import { GrantsPanel } from "../features/settings/GrantsPanel";
import { SpacesPanel } from "../features/settings/SpacesPanel";
import { SecurityPolicyBadge } from "../features/settings/SecurityPolicyBadge";

const tabs = [
  { to: "/settings/session", label: "Session" },
  { to: "/settings/keys", label: "Keys & accounts" },
  { to: "/settings/identities", label: "Identities" },
  { to: "/settings/grants", label: "Grants" },
  { to: "/settings/spaces", label: "Spaces" },
] as const;

function panelFor(pathname: string) {
  if (pathname.includes("/keys")) return <KeysAccountsPanel />;
  if (pathname.includes("/identities")) return <IdentitiesPanel />;
  if (pathname.includes("/grants")) return <GrantsPanel />;
  if (pathname.includes("/spaces")) return <SpacesPanel />;
  return <SessionPanel />;
}

export function SettingsPage() {
  const { pathname } = useLocation();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage API session, keys, identities, grants, and spaces for this OHM instance.
        </p>
      </div>

      <nav
        className="flex flex-wrap gap-1 border-b border-slate-200 dark:border-slate-700"
        aria-label="Settings"
      >
        {tabs.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              [
                "border-b-2 px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "border-indigo-600 text-indigo-700 dark:border-indigo-400 dark:text-indigo-300"
                  : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100",
              ].join(" ")
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>

      {panelFor(pathname)}

      <footer className="border-t border-slate-200 pt-4 dark:border-slate-700">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">
          Security policy
        </p>
        <SecurityPolicyBadge />
      </footer>
    </div>
  );
}
