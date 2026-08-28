"use client";

import Link from "next/link";
import { PageHero } from "../../components/layout/PageHero";
import {
  ACCOUNT_GROUP,
  UNLISTED_GROUP,
  NAV_GROUPS,
} from "../../components/layout/nav";
import { SHORTCUTS } from "../../components/layout/shortcuts";
import { SECTION_LABEL_SM } from "../../components/ui/typography";
import { SectionHeading } from "../../components/ui/SectionHeading";
import { PANEL } from "../../components/ui/surface";
import { cn } from "@/lib/utils";

/**
 * Help: the sitemap, the keyboard contract, and the accessibility features,
 * generated from the same data the chrome uses.
 *
 * NAV_GROUPS and SHORTCUTS are the sources, so a route or shortcut added to
 * either appears here without anyone remembering to update a page. Help that
 * is hand-maintained drifts, and drifted help is worse than none.
 */

/**
 * How to drive this app without a mouse, without motion, without small text.
 *
 * This section has been rewritten twice and the reason is worth keeping. It
 * began as a conformance report — "twenty variants, measured from the
 * runtime-resolved token values rather than numbers copied into a test" — which
 * is true, and addressed to an auditor. The rewrite turned it into prose about
 * features, which was closer and still not usable: a person who needs to skip a
 * navigation block does not want a paragraph, they want the key.
 *
 * So each row is a control and its effect, in the same key-chip shape the
 * shortcuts table above uses, because these ARE shortcuts — they just answer
 * "how do I cope with this page" rather than "where do I go next". `keys` is
 * rendered as <kbd>; `hint` is the plain-language alternative for anything that
 * is a setting rather than a keystroke.
 */
const A11Y: Array<{ keys?: string[]; hint?: string; desc: string }> = [
  {
    keys: ["Tab"],
    desc: "from the top of any page, jumps to “Skip to content” — past the header and the menu, straight into the page itself",
  },
  { keys: ["?"], desc: "every shortcut, without leaving the page" },
  {
    keys: ["Esc"],
    desc: "closes any menu or dialog and puts focus back on the control that opened it",
  },
  { keys: ["m"], desc: "light / dark, immediately" },
  {
    keys: ["t"],
    desc: "next theme. Mono and Terminal are the plainest of the ten; every one is contrast-checked in both light and dark",
  },
  {
    keys: ["Ctrl", "+"],
    desc: "browser zoom, up to 200% — the layout reflows instead of clipping or scrolling sideways (⌘ on a Mac)",
  },
  {
    hint: "System setting",
    desc: "turn on “reduce motion” in your OS accessibility settings and this app follows: the loading mark stops, menus stop sliding, nothing moves on its own",
  },
  {
    hint: "Screen reader",
    desc: "one heading names each page, panels are labelled regions you can jump between, the current page is marked in the menu, and the result of an action is announced when it happens",
  },
];

export function HelpView() {
  return (
    <div className="space-y-8">
      {/* The three terms are this page's three sections, so they are its own
          table of contents rather than a description of it. Same ids the
          section headings already publish as permalinks. */}
      <PageHero
        title="Help"
        crumb={[
          { label: "routes", href: "#h-routes" },
          { label: "shortcuts", href: "#h-keys" },
          { label: "accessibility", href: "#h-a11y" },
        ]}
      />

      <section aria-labelledby="h-routes" className="space-y-4">
        <SectionHeading id="h-routes" role="label">
          Where things are
        </SectionHeading>
        {/*
          UNLISTED_GROUP is here and not in the drawer. The drawer is a menu —
          a list of places worth going — while this is the sitemap, and a route
          the chrome binds a chord to has to appear on the page that documents
          the chords. /icons moved out of the menu for exactly that reason and
          would otherwise have a key nothing explains.
        */}
        {[...NAV_GROUPS, ACCOUNT_GROUP, UNLISTED_GROUP].map((group) => (
          <div key={group.label} className={PANEL}>
            <h3 className={cn(SECTION_LABEL_SM, "mb-3")}>{group.label}</h3>
            <ul className="m-0 grid list-none gap-3 p-0 sm:grid-cols-2">
              {group.entries.map((entry) => {
                const Icon = entry.icon;
                return (
                  /*
                    The glyph sits on the title's line, centred against it, and
                    the description hangs under both. It used to be a column of
                    its own nudged down by a hand-picked `mt-0.5`, which held
                    only while every glyph had the same optical height — the
                    tightened viewBoxes gave each one its own, and the margin
                    started missing in both directions. `items-center` on the
                    title row aligns them by construction; `pl-6` under it is
                    the icon plus its gap, so the description keeps the same
                    left edge.
                  */
                  <li key={entry.href} className="min-w-0">
                    <span className="flex items-center gap-2">
                      <Icon
                        aria-hidden="true"
                        className={`h-4 w-4 shrink-0 ${group.accent}`}
                      />
                      {entry.external ? (
                        <a
                          href={entry.href}
                          className="inline-flex min-h-6 items-center truncate text-sm font-medium text-primary-ink hover:underline"
                        >
                          {entry.name}
                        </a>
                      ) : (
                        <Link
                          href={entry.href}
                          className="inline-flex min-h-6 items-center truncate text-sm font-medium text-primary-ink hover:underline"
                        >
                          {entry.name}
                        </Link>
                      )}
                    </span>
                    <span className="block pl-6 text-xs text-muted-foreground">
                      {entry.desc}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
        <p className="text-xs text-muted-foreground">
          Design, facility, and package detail pages are reached from their
          lists. A supply tree opens from the match that produced it — it is a
          result, not a browsable collection.
        </p>
      </section>

      <section aria-labelledby="h-keys" className="space-y-3">
        <SectionHeading id="h-keys" role="label">
          Keyboard shortcuts
        </SectionHeading>
        <div className={PANEL}>
          <ul className="m-0 grid list-none gap-x-6 gap-y-2 p-0 sm:grid-cols-2">
            {SHORTCUTS.map((s) => (
              <li
                key={s.keys.join("+")}
                className="flex items-baseline gap-2 text-sm"
              >
                <span className="flex shrink-0 gap-1">
                  {/* Indexed: a chord can repeat a key — `g` then `g` opens Generate. */}
                  {s.keys.map((k, i) => (
                    <kbd
                      key={`${k}-${i}`}
                      className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-xs text-foreground"
                    >
                      {k}
                    </kbd>
                  ))}
                </span>
                <span className="text-muted-foreground">{s.desc}</span>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs text-muted-foreground">
            Shortcuts are ignored while typing in a field, so a search box takes
            <kbd className="mx-1 rounded border border-border bg-muted px-1 py-0.5 font-mono">
              g
            </kbd>
            as a letter.
          </p>
        </div>
      </section>

      <section aria-labelledby="h-a11y" className="space-y-3">
        <SectionHeading id="h-a11y" role="label">
          Accessibility
        </SectionHeading>
        <div className={PANEL}>
          <ul className="m-0 grid list-none gap-x-6 gap-y-2 p-0 sm:grid-cols-2">
            {A11Y.map((item) => (
              <li key={item.desc} className="flex items-baseline gap-2 text-sm">
                <span className="flex shrink-0 gap-1">
                  {item.keys?.map((k, i) => (
                    <kbd
                      key={`${k}-${i}`}
                      className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-xs text-foreground"
                    >
                      {k}
                    </kbd>
                  ))}
                  {/* A setting rather than a keystroke: same column, no key cap,
                    because a <kbd> around "System setting" would tell a screen
                    reader it is a key to press. */}
                  {item.hint && (
                    <span className="rounded border border-dashed border-border px-1.5 py-0.5 text-xs text-muted-foreground">
                      {item.hint}
                    </span>
                  )}
                </span>
                <span className="text-muted-foreground">{item.desc}</span>
              </li>
            ))}
          </ul>
        </div>
        {/* Kept, and moved to the end where it reads as an invitation rather
            than as the section's subject. It is the one line here addressed to
            the reader as a reporter instead of as a user, and it earns its
            place: the promise it makes is what the cards above are worth. */}
        <p className="text-xs text-muted-foreground">
          If something here blocks you, please open an issue and say what you
          were trying to do — accessibility defects are treated as bugs, not
          enhancements, and “it works with a mouse” is not a resolution.
        </p>
      </section>
    </div>
  );
}
