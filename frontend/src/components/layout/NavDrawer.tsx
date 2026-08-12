"use client";

import { useEffect, useRef, useState } from "react";
import { CHECKBOX, CHOICE_ROW, FIELD } from "../../components/ui/field";
import { createPortal } from "react-dom";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQueryClient, useIsFetching } from "@tanstack/react-query";
import { FlaskConical, Link2, RefreshCw, X } from "lucide-react";
import { ShowcaseIcon } from "../icons";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";
import { useThemeSwatches } from "../../hooks/useThemeSwatches";
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
import { useDialogFocus } from "../../lib/useDialogFocus";
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
 * The length of both eases, in ms. Kept in step with `duration-200` on the
 * panel: this is how long the exiting drawer stays mounted, so a shorter value
 * cuts the slide off and a longer one leaves a finished animation on screen.
 */
const EASE_MS = 200;

/**
 * Whether the visitor has asked for less motion.
 *
 * Read at the moment of closing rather than subscribed to: the panel's own
 * `motion-reduce:animate-none` already handles the drawing, and what this
 * decides is whether to hold the unmount for an animation that will not play.
 */
function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

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
 * with both animations inside the reduced-motion guard.
 *
 * It eases out as well as in. Closing used to be an unmount, which is less a
 * dismissal than a disappearance: the panel that took 200ms to arrive was
 * simply not there on the next frame. So `open` going false starts the exit
 * and the unmount waits for it. That is why the modal contract is keyed on
 * `open` and not on being mounted — the drawer stops being modal the moment it
 * starts leaving. Focus returns to the opener, Escape and the scroll lock are
 * released, and the panel is inert for the beat it spends sliding out.
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
  // Only while the picker is on screen — see the hook: resolving costs ten
  // forced style recalcs, and a closed drawer has nothing to draw with them.
  const swatches = useThemeSwatches(open);
  const queryClient = useQueryClient();
  const isFetching = useIsFetching() > 0;
  const panelRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);
  // The exit, and the only reason the panel outlives `open`.
  const [leaving, setLeaving] = useState(false);
  const wasOpen = useRef(open);

  // Focus management: close button first, trap Tab inside, Esc closes, focus
  // returns to the opener the moment the drawer stops being modal. Shared with
  // the site-layer gate — see lib/useDialogFocus.ts.
  useDialogFocus(panelRef, { active: open, onClose });

  // Whether to render is decided HERE, in render, not in an effect. The trap
  // above reads panelRef in its own effect, on the commit where `open` turns
  // true — so a panel that waits for an effect to mount it is not in the tree
  // yet when the trap looks for it, and the drawer opens with no focus, no
  // scroll lock, and no Escape. Only the exit needs state, because only the
  // exit outlasts the prop.
  useEffect(() => {
    const dismissed = wasOpen.current && !open;
    wasOpen.current = open;
    if (open) {
      setLeaving(false);
      return;
    }
    if (!dismissed || prefersReducedMotion()) return;
    setLeaving(true);
    const timer = window.setTimeout(() => setLeaving(false), EASE_MS);
    return () => window.clearTimeout(timer);
  }, [open]);

  // Close on route change — a chosen destination is the natural dismissal.
  useEffect(() => {
    onClose();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- pathname is the trigger; onClose is stable
  }, [pathname]);

  if (!open && !leaving) return null;

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
    // Nothing catches a click on the way out: the overlay is still on screen
    // for the length of the exit, and a dismissed menu that eats the click
    // meant for what is behind it is worse than one that vanishes.
    <div
      className={`fixed inset-0 ${leaving ? "pointer-events-none" : ""}`}
      style={{ zIndex: "var(--z-overlay)" }}
    >
      <div
        className={`absolute inset-0 bg-black/50 duration-150 motion-reduce:animate-none ${
          leaving
            ? "animate-out fade-out ease-in"
            : "animate-in fade-in ease-out"
        }`}
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Out on the same curve it came in on, reversed: ease-out to arrive
          (fast, then settling) and ease-in to leave (gathering speed as it
          goes). Both are transform and opacity, so the compositor draws them
          and no amount of work on the main thread can stutter the slide. */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal={leaving ? undefined : true}
        aria-label="Site menu"
        id="site-menu"
        inert={leaving}
        className={`absolute right-0 top-0 flex h-full w-full max-w-sm flex-col overflow-y-auto border-l border-border bg-card shadow-xl duration-200 motion-reduce:animate-none ${
          leaving
            ? "animate-out slide-out-to-right ease-in"
            : "animate-in slide-in-from-right ease-out"
        }`}
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
            <NavGroupBlock
              key={group.label}
              group={group}
              pathname={pathname}
            />
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

        <fieldset className="min-w-0 shrink-0 border-t border-border px-2 py-2">
          <legend className="sr-only">Theme</legend>
          <p aria-hidden="true" className={LABEL}>
            Theme
          </p>
          {/* Tighter than it looks it can be. The rows stay 44px, because that
              is the target size the accessibility page promises and the
              responsive gate measures — what came out is the air INSIDE them:
              the chip was a small pill floating in a tall row, so ten worlds
              read as ten widely spaced words. The chip now fills its row's
              height, which closes the gaps without moving a target edge. */}
          <div className="grid grid-cols-2 gap-x-1.5 px-1">
            {themes.map(({ slug, label }) => {
              const swatch = swatches[slug];
              return (
                <label key={slug} className={CHOICE_ROW}>
                  <input
                    type="radio"
                    name="ohm-theme-pick"
                    value={slug}
                    checked={theme === slug}
                    onChange={() => setTheme(slug)}
                    className={CHECKBOX}
                  />
                  {/*
                    The row IS the preview: the name in that world's accent and
                    typeface, ON that world's own ground.

                    The name alone was not enough. Ten worlds do not have ten
                    accents — Warm, Zine, Terminal, Synthwave and Bubblegum all
                    land on a magenta — so five rows painted the same colour and
                    the reader chose between them by word. The ground is what
                    actually separates them, and it is most of what a world
                    looks like: cream, near-black, ink-blue. Now each row shows
                    it.

                    swatch.ink, not swatch.accent: raw accents sit between
                    3.8:1 and 4.5:1 as ink in several worlds — the finding
                    behind --color-primary-ink. It is now solved against THAT
                    world's ground rather than the drawer's, because that is
                    the surface the text lands on here.
                  */}
                  <span
                    className="min-w-0 flex-1 truncate rounded px-1.5 py-1.5"
                    style={
                      swatch
                        ? {
                            fontFamily: swatch.fontSans,
                            color: swatch.ink,
                            backgroundColor: swatch.ground,
                            // An edge in the world's own border colour, so a
                            // chip whose ground is near the drawer's does not
                            // dissolve into it.
                            boxShadow: `inset 0 0 0 1px ${swatch.edge}`,
                          }
                        : undefined
                    }
                  >
                    {label}
                  </span>
                </label>
              );
            })}
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
          </button>
        </fieldset>

        <div className="shrink-0 border-t border-border px-4 py-2">
          <div className="flex items-center justify-between gap-2 pb-1">
            <p className="text-[0.6875rem] font-semibold uppercase tracking-wider text-muted-foreground">
              Keyboard
            </p>
            {/*
              The glyph gallery, as a glyph. It used to be a full Reference row
              — icon, name and a role line — for a page that documents the icon
              set rather than being somewhere to go. One mark of the thing it
              leads to is the whole label it needs; the accessible name carries
              the rest, and the 44px box keeps it a real target next to a
              heading that is not one.
            */}
            <Link
              href="/icons"
              onClick={onClose}
              title="Icons"
              className="-mr-2 flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <ShowcaseIcon aria-hidden="true" className="h-4 w-4" />
              <span className="sr-only">Icons — the glyph set</span>
            </Link>
          </div>
          <ul className="m-0 grid list-none grid-cols-1 gap-x-4 gap-y-0.5 p-0 sm:grid-cols-2">
            {SHORTCUTS.map((s) => (
              <li
                key={s.keys.join("+")}
                className="flex items-baseline gap-2 text-xs"
              >
                <span className="flex shrink-0 gap-1">
                  {/* Indexed: a chord can repeat a key — `g` then `g` opens Generate. */}
                  {s.keys.map((k, i) => (
                    <kbd
                      key={`${k}-${i}`}
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
