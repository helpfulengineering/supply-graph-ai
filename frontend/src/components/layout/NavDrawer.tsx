"use client";

import { useEffect, useRef, useState } from "react";
import { FIELD } from "../../components/ui/field";
import { createPortal } from "react-dom";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQueryClient, useIsFetching } from "@tanstack/react-query";
import { FlaskConical, Gauge, Link2, RefreshCw, Settings } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";
import { refreshLowVolatilityData } from "../../queryClient";
import { NAV_GROUPS, isActivePath } from "./nav";
import { SHORTCUTS } from "./shortcuts";
import { useSiteLayer } from "../../lib/site/useSiteLayer";
import { useDialogFocus } from "../../lib/useDialogFocus";
import { demoModeEnabled, setDemoMode } from "../../lib/demo/demoMode";

interface NavDrawerProps {
  open: boolean;
  onClose: () => void;
}

/**
 * The hamburger sitemap: every route in the app, grouped, each entry carrying
 * a role line. ARIA disclosure semantics — dialog, focus trap, Esc, backdrop —
 * with the entrance animation inside the reduced-motion guard.
 *
 * Rendered only while open: unmounting is the exit path, so focus restoration
 * (in the cleanup effect) and the axe animation-settling contract stay simple.
 */
export function NavDrawer({ open, onClose }: NavDrawerProps) {
  const pathname = usePathname() ?? "";
  const { isAdmin, token } = useAuth();
  const site = useSiteLayer();
  const { isDark, toggle, theme, setTheme, themes, shareUrl } = useTheme();
  const queryClient = useQueryClient();
  const isFetching = useIsFetching() > 0;
  const panelRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);

  // Focus management: close button first, trap Tab inside, Esc closes, focus
  // returns to the opener when the drawer unmounts. Shared with the site-layer
  // gate — see lib/useDialogFocus.ts.
  useDialogFocus(panelRef, { active: open, onClose });

  // Close on route change — a chosen destination is the natural dismissal.
  useEffect(() => {
    onClose();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- pathname is the trigger, onClose is stable-enough chrome state
  }, [pathname]);

  if (!open) return null;

  const settingsLabel = isAdmin ? "Settings" : token ? "Session" : "Connect";
  const settingsDesc = isAdmin
    ? "instance administration panels"
    : token
      ? "your API session"
      : "paste an API key to enable writes";

  const itemClass = (active: boolean) =>
    [
      "flex min-h-11 items-start gap-2.5 rounded-md px-3 py-2 no-underline transition-colors",
      active
        ? "bg-accent text-primary-ink shadow-glow-sm"
        : "text-foreground hover:bg-muted",
    ].join(" ");

  // Portal to <body>: rendered in place, the drawer would inherit the sticky
  // header's stacking context (z-40) and lose to Leaflet's panes (z~400), so
  // the map bled through the backdrop. From <body> the wrapper competes at
  // root with the token scale's top layer.
  return createPortal(
    <div className="fixed inset-0" style={{ zIndex: "var(--z-overlay)" }}>
      <div
        className="absolute inset-0 bg-black/50 animate-in fade-in duration-150 motion-reduce:animate-none"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Site menu"
        id="site-menu"
        className="absolute right-0 top-0 flex h-full w-full max-w-sm flex-col overflow-y-auto border-l border-border bg-card shadow-xl animate-in slide-in-from-right duration-200 motion-reduce:animate-none"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <span className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Menu
          </span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close menu"
            className="flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <svg
              aria-hidden="true"
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        <nav aria-label="Primary navigation" className="flex-1 px-3 py-2">
          {NAV_GROUPS.map((group) => (
            <div key={group.label} className="py-2">
              <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {group.label}
              </p>
              <ul className="m-0 list-none p-0">
                {group.entries.map((entry) => {
                  const active = !entry.external && isActivePath(pathname, entry.href);
                  const Icon = entry.icon;
                  const body = (
                    <>
                      <Icon
                        aria-hidden="true"
                        className={`mt-0.5 h-4 w-4 shrink-0 ${group.accent}`}
                      />
                      <span className="min-w-0">
                        <span className="block text-sm font-medium">{entry.name}</span>
                        <span className="block text-xs text-muted-foreground">
                          {entry.desc}
                        </span>
                      </span>
                    </>
                  );
                  return (
                    <li key={entry.href}>
                      {entry.external ? (
                        <a href={entry.href} className={itemClass(false)}>
                          {body}
                        </a>
                      ) : (
                        <Link
                          href={entry.href}
                          aria-current={active ? "page" : undefined}
                          className={itemClass(active)}
                        >
                          {body}
                        </Link>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}

          <div className="py-2">
            <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Account
            </p>
            <Link
              href="/settings/session"
              aria-current={isActivePath(pathname, "/settings") ? "page" : undefined}
              className={itemClass(isActivePath(pathname, "/settings"))}
            >
              <Settings
                aria-hidden="true"
                className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
              />
              <span className="min-w-0">
                <span className="block text-sm font-medium">{settingsLabel}</span>
                <span className="block text-xs text-muted-foreground">{settingsDesc}</span>
              </span>
            </Link>
          </div>

          {/* Site layer: absent entirely when the instance did not opt in.
              Not disabled, not explained — on the default deployment the
              capability does not exist, so the nav simply has no entry. */}
          {site.enabled && (
            <div className="py-2">
              <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Site
              </p>
              <Link
                href="/mission-control"
                aria-current={isActivePath(pathname, "/mission-control") ? "page" : undefined}
                className={itemClass(isActivePath(pathname, "/mission-control"))}
              >
                <Gauge
                  aria-hidden="true"
                  className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
                />
                <span className="min-w-0">
                  <span className="block text-sm font-medium">Mission Control</span>
                  <span className="block text-xs text-muted-foreground">
                    telemetry and visitor records for this site
                  </span>
                </span>
              </Link>
            </div>
          )}

          <div className="py-2">
            <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Data
            </p>
            <button
              type="button"
              onClick={() => setDemoMode(!demoModeEnabled())}
              aria-pressed={demoModeEnabled()}
              className="flex min-h-11 w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-medium text-foreground transition-colors hover:bg-muted"
            >
              <FlaskConical aria-hidden="true" className="h-4 w-4" />
              Demo data
              <span className="ml-auto text-xs font-normal text-muted-foreground">
                {demoModeEnabled() ? "on — using sample world" : "explore with a sample world"}
              </span>
            </button>

            <button
              type="button"
              onClick={() => refreshLowVolatilityData(queryClient)}
              disabled={isFetching}
              className="flex min-h-11 w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-medium text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RefreshCw
                aria-hidden="true"
                className={`h-4 w-4 ${isFetching ? "animate-spin motion-reduce:animate-none" : ""}`}
              />
              Refresh data
              <span className="ml-auto text-xs font-normal text-muted-foreground">
                designs and facilities
              </span>
            </button>
          </div>
        </nav>

        <fieldset className="border-t border-border px-5 py-4">
          <legend className="sr-only">Theme</legend>
          <p
            aria-hidden="true"
            className="pb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground"
          >
            Theme
          </p>
          <div className="grid grid-cols-2 gap-1">
            {themes.map(({ slug, label }) => (
              <label
                key={slug}
                className="flex min-h-11 cursor-pointer items-center gap-2 rounded-md px-2 text-sm text-foreground transition-colors hover:bg-muted"
              >
                <input
                  type="radio"
                  name="ohm-theme-pick"
                  value={slug}
                  checked={theme === slug}
                  onChange={() => setTheme(slug)}
                  className="accent-[var(--ttm-accent-cta)]"
                />
                {label}
              </label>
            ))}
          </div>
          <button
            type="button"
            onClick={toggle}
            aria-pressed={isDark}
            className={`${FIELD} mt-3 flex min-h-11 w-full items-center justify-between hover:bg-muted`}
          >
            <span>{isDark ? "Dark mode" : "Light mode"}</span>
            <span className="text-xs text-muted-foreground">switch to {isDark ? "light" : "dark"}</span>
          </button>
        </fieldset>

        <div className="px-3 pb-1">
          <button
            type="button"
            onClick={() => {
              void navigator.clipboard?.writeText(shareUrl());
              setCopied(true);
            }}
            className="flex min-h-11 w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-medium text-foreground transition-colors hover:bg-muted"
          >
            <Link2 aria-hidden="true" className="h-4 w-4 text-muted-foreground" />
            {copied ? "Link copied" : "Copy link with this look"}
            <span className="ml-auto text-xs font-normal text-muted-foreground">
              theme + mode in the URL
            </span>
          </button>
        </div>

        <div className="border-t border-border px-3 py-4">
          <p className="pb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Keyboard
          </p>
          <ul className="m-0 grid list-none grid-cols-1 gap-x-4 gap-y-1 p-0 sm:grid-cols-2">
            {SHORTCUTS.map((s) => (
              <li key={s.keys.join("+")} className="flex items-baseline gap-2 text-xs">
                <span className="flex shrink-0 gap-1">
                  {s.keys.map((k) => (
                    <kbd
                      key={k}
                      className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[0.6875rem] text-foreground"
                    >
                      {k}
                    </kbd>
                  ))}
                </span>
                <span className="text-muted-foreground">{s.desc}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>,
    document.body,
  );
}
