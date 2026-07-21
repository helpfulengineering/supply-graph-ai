import { NavLink } from "react-router-dom";
import { useQueryClient, useIsFetching } from "@tanstack/react-query";
import { useTheme } from "../../context/ThemeContext";
import { useAuth } from "../../context/AuthContext";
import { refreshLowVolatilityData } from "../../queryClient";

const navItems = [
  { to: "/okh", label: "Designs", icon: "🔩" },
  { to: "/facilities", label: "Facilities", icon: "🏭" },
  { to: "/match", label: "Match", icon: "⚡" },
  // Saved solutions are per-search, user-specific, and go stale fast — a supply
  // tree is reached directly from its match (and can be downloaded), so there is
  // no browse list. Revisit as user-scoped history once auth lands.
  // RFQ stays dormant in v1 nav; Packages promoted in F2b.
] as const;

export function NavBar() {
  const { isDark, toggle } = useTheme();
  const { isAdmin } = useAuth();
  const queryClient = useQueryClient();
  const isFetching = useIsFetching() > 0;

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="mx-auto flex max-w-7xl items-center gap-6 px-6 py-3">
        <NavLink to="/" className="flex items-center gap-2 text-lg font-bold text-indigo-600 no-underline dark:text-indigo-400">
          <span aria-hidden="true">🌐</span>
          <span>OHM</span>
        </NavLink>

        <nav className="flex gap-1" aria-label="Primary navigation">
          {navItems.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                [
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100",
                ].join(" ")
              }
            >
              <span aria-hidden="true">{icon}</span>
              {label}
            </NavLink>
          ))}
          {isAdmin && (
            <NavLink
              to="/settings/session"
              className={({ isActive }) =>
                [
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100",
                ].join(" ")
              }
            >
              <span aria-hidden="true">⚙</span>
              Settings
            </NavLink>
          )}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <button
            onClick={() => refreshLowVolatilityData(queryClient)}
            disabled={isFetching}
            aria-label="Refresh data"
            title="Refresh designs and facilities from the latest data"
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-50 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M21 12a9 9 0 1 1-2.64-6.36" />
              <path d="M21 3v6h-6" />
            </svg>
          </button>

          <button
            onClick={toggle}
            aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition-colors"
          >
            {isDark ? (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 3a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0V4a1 1 0 0 1 1-1zm0 15a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0v-1a1 1 0 0 1 1-1zm9-9a1 1 0 1 1 0 2h-1a1 1 0 1 1 0-2h1zM4 12a1 1 0 1 1 0 2H3a1 1 0 1 1 0-2h1zm14.95-6.364a1 1 0 0 1 0 1.414l-.707.707a1 1 0 1 1-1.414-1.414l.707-.707a1 1 0 0 1 1.414 0zM6.757 17.657a1 1 0 0 1 0 1.414l-.707.707a1 1 0 1 1-1.414-1.414l.707-.707a1 1 0 0 1 1.414 0zm11.9 1.414a1 1 0 1 1-1.414-1.414l.707-.707a1 1 0 0 1 1.414 1.414l-.707.707zM7.05 5.636a1 1 0 0 1-1.414 1.414l-.707-.707a1 1 0 0 1 1.414-1.414l.707.707zM12 7a5 5 0 1 1 0 10A5 5 0 0 1 12 7z"/>
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z"/>
              </svg>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
