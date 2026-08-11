"use client";

import { useEffect, useRef, useState } from "react";
import { FIELD } from "../../components/ui/field";
import { createPortal } from "react-dom";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQueryClient, useIsFetching } from "@tanstack/react-query";
import { FlaskConical, Link2, RefreshCw, X } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";
import { refreshLowVolatilityData } from "../../queryClient";
import {
  ACCOUNT_GROUP,
  NAV_GROUPS,
  SITE_GROUP,
  isActivePath,
  navEntryPath,
  type NavEntry,
  type NavGroup,
} from "./nav";
import { SHORTCUTS } from "./shortcuts";
import { useSiteLayer } from "../../lib/site/useSiteLayer";
import { demoModeEnabled, setDemoMode } from "../../lib/demo/demoMode";

interface NavDrawerProps {
  open: boolean;
  onClose: () => void;
}

/** Section label. One rhythm for the sitemap groups and the panels below. */
const LABEL =
  "px-3 pb-0.5 text-[0.6875rem] font-semibold uppercase tracking-wider text-muted-foreground";

/** A row in the drawer, whether it navigates or acts. */
const ROW =
  "flex min-h-11 w-full items-center gap-2.5 rounded-md py-1.5 pl-3 pr-2.5 text-left text-sm font-medium transition-colors";

const IRIDESCENT =
  "linear-gradient(120deg, var(--ttm-irid-a), var(--ttm-irid-b), var(--ttm-irid-c), var(--ttm-irid-d), var(--ttm-irid-e))";

/**
 * One sitemap row.
 *
 * The active row carries an iridescent rail on its leading edge — the same
 * gradient that closes every page hero, turned on its side. It is the drawer's
 * half of a handshake the hero completes: you leave the menu at a rail and
 * arrive under a rule, in the brand's own colours, with the entry's icon
 * unchanged between the two.
 */
function NavRow({
  entry,
  group,
  pathname,
}: {
  entry: NavEntry;
  group: NavGroup;
  pathname: string;
}) {
  const active = !entry.external && isActivePath(pathname, navEntryPath(entry));
  const Icon = entry.icon;
  const className = [
    "relative no-underline",
    ROW,
    active
      ? "bg-accent text-primary-ink shadow-glow-sm"
      : "text-foreground hover:bg-muted",
  ].join(" ");

  const body = (
    <>
      {active && (
        <span
          aria-hidden="true"
          className="absolute inset-y-1 left-0 w-0.5 rounded-full"
          style={{
            background:
              "linear-gradient(180deg, var(--ttm-irid-a), var(--ttm-irid-c), var(--ttm-irid-e))",
          }}
        />
      )}
      <Icon aria-hidden="true" className={`h-4 w-4 shrink-0 ${group.accent}`} />
      <span className="min-w-0">
        <span className="block leading-tight">{entry.name}</span>
        <span className="block text-xs font-normal leading-tight text-muted-foreground">
          {entry.desc}
        </span>
      </span>
    </>
  );

  return entry.external ? (
    <a href={entry.href} className={className}>
      {body}
    </a>
  ) : (
    <Link
      href={entry.href}
      aria-current={active ? "page" : undefined}
      className={className}
    >
      {body}
    </Link>
  );
}

function NavGroupBlock({
  group,
  pathname,
}: {
  group: NavGroup;
  pathname: string;
}) {
  return (
    <div className="pb-1.5">
      <p className={LABEL}>{group.label}</p>
      <ul className="m-0 list-none p-0">
        {group.entries.map((entry) => (
          <li key={entry.href}>
            <NavRow entry={entry} group={group} pathname={pathname} />
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * The hamburger sitemap: every route in the app, grouped, each entry carrying
 * a role line. ARIA disclosure semantics — dialog, focus trap, Esc, backdrop —
 * with the entrance animation inside the reduced-motion guard.
 *
 * Rendered only while open: unmounting is the exit path, so focus restoration
 * (in the cleanup effect) and the axe animation-settling contract stay simple.
 *
 * Density is deliberate. The drawer holds the whole sitemap plus the theme,
 * data, and keyboard panels, and at the old rhythm — 20px gutters, a full line
 * of padding above and below every group, a section of its own for a single
 * copy-link button — Reference fell below the fold on a laptop, so "everything
 * is here" was a claim you had to scroll to check. The space came out of the
 * chrome between rows, never out of the rows: every control still clears the
 * 44px target the accessibility page promises, and `min-h-11` in ROW is what
 * says so.
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

  // Focus management: close button first, trap Tab inside, Esc closes,
  // focus returns to the opener when the drawer unmounts.
  useEffect(() => {
    if (!open) return;
    const opener = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    if (!panel) return;

    const focusables = () =>
      Array.from(
        panel.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      );
    focusables()[0]?.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key !== "Tab") return;
      const items = focusables();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
      opener?.focus();
    };
  }, [open, onClose]);

  // Close on route change — a chosen destination is the natural dismissal.
  useEffect(() => {
    onClose();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- pathname is the trigger, onClose is stable-enough chrome state
  }, [pathname]);

  if (!open) return null;

  // The one label the sitemap cannot state, because it depends on what you
  // hold: the same route is Connect, Session, or Settings depending on whether
  // there is an API key and on what it is allowed to do. Route, icon, and
  // accent still come from the sitemap, so Help and the page hero show the
  // same row this does.
  const accountGroup: NavGroup = {
    ...ACCOUNT_GROUP,
    entries: [
      {
        ...ACCOUNT_GROUP.entries[0],
        name: isAdmin ? "Settings" : token ? "Session" : "Connect",
        desc: isAdmin
          ? "instance administration panels"
          : token
            ? "your API session"
            : "paste an API key to enable writes",
      },
    ],
  };

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
        <div className="flex shrink-0 items-center justify-between px-4 py-1.5">
          <span className="text-[0.6875rem] font-semibold uppercase tracking-wider text-muted-foreground">
            Menu
          </span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close menu"
            className="-mr-1.5 flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <X aria-hidden="true" className="h-5 w-5" />
          </button>
        </div>
        {/* The brand rule as the drawer's masthead border — the same gradient
            that closes every page hero, so chrome and page read as one
            system rather than as a menu bolted onto a document. */}
        <div
          aria-hidden="true"
          className="h-px shrink-0"
          style={{ background: IRIDESCENT }}
        />

        <nav aria-label="Primary navigation" className="flex-1 px-2 pt-2">
          {NAV_GROUPS.map((group) => (
            <NavGroupBlock key={group.label} group={group} pathname={pathname} />
          ))}

          <NavGroupBlock group={accountGroup} pathname={pathname} />

          {/* Site layer: absent entirely when the instance did not opt in.
              Not disabled, not explained — on the default deployment the
              capability does not exist, so the nav simply has no entry. */}
          {site.enabled && (
            <NavGroupBlock group={SITE_GROUP} pathname={pathname} />
          )}

          <div className="pb-1.5">
            <p className={LABEL}>Data</p>
            <button
              type="button"
              onClick={() => setDemoMode(!demoModeEnabled())}
              aria-pressed={demoModeEnabled()}
              className={`${ROW} text-foreground hover:bg-muted`}
            >
              <FlaskConical aria-hidden="true" className="h-4 w-4 shrink-0" />
              Demo data
              <span className="ml-auto text-right text-xs font-normal leading-tight text-muted-foreground">
                {demoModeEnabled()
                  ? "on — using sample world"
                  : "explore with a sample world"}
              </span>
            </button>

            <button
              type="button"
              onClick={() => refreshLowVolatilityData(queryClient)}
              disabled={isFetching}
              className={`${ROW} text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50`}
            >
              <RefreshCw
                aria-hidden="true"
                className={`h-4 w-4 shrink-0 ${isFetching ? "animate-spin motion-reduce:animate-none" : ""}`}
              />
              Refresh data
              <span className="ml-auto text-xs font-normal text-muted-foreground">
                designs and facilities
              </span>
            </button>
          </div>
        </nav>

        <fieldset className="shrink-0 border-t border-border px-2 py-2">
          <legend className="sr-only">Theme</legend>
          <p aria-hidden="true" className={LABEL}>
            Theme
          </p>
          <div className="grid grid-cols-2 gap-x-2 px-1">
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
            className={`${FIELD} mx-1 mt-1.5 flex min-h-11 w-[calc(100%-0.5rem)] items-center justify-between hover:bg-muted`}
          >
            <span>{isDark ? "Dark mode" : "Light mode"}</span>
            <span className="text-xs text-muted-foreground">
              switch to {isDark ? "light" : "dark"}
            </span>
          </button>
          {/* Sharing the look belongs with the controls that set it. It used to
              sit in a section of its own between Theme and Keyboard, which
              spent a whole band of the drawer on one button. */}
          <button
            type="button"
            onClick={() => {
              void navigator.clipboard?.writeText(shareUrl());
              setCopied(true);
            }}
            className={`${ROW} text-foreground hover:bg-muted`}
          >
            <Link2 aria-hidden="true" className="h-4 w-4 shrink-0" />
            {copied ? "Link copied" : "Copy link with this look"}
            <span className="ml-auto text-xs font-normal text-muted-foreground">
              theme + mode in the URL
            </span>
          </button>
        </fieldset>

        <div className="shrink-0 border-t border-border px-4 py-2">
          <p className="pb-1 text-[0.6875rem] font-semibold uppercase tracking-wider text-muted-foreground">
            Keyboard
          </p>
          <ul className="m-0 grid list-none grid-cols-1 gap-x-4 gap-y-0.5 p-0 sm:grid-cols-2">
            {SHORTCUTS.map((s) => (
              <li
                key={s.keys.join("+")}
                className="flex items-baseline gap-2 text-xs"
              >
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
