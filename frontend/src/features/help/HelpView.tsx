"use client";

import Link from "next/link";
import { PageHero } from "../../components/layout/PageHero";
import { ACCOUNT_GROUP, NAV_GROUPS } from "../../components/layout/nav";
import { SHORTCUTS } from "../../components/layout/shortcuts";
import {
  CARD_TITLE,
  SECTION_LABEL,
  SECTION_LABEL_SM,
} from "../../components/ui/typography";
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
 * What a reader can DO, not what the build was measured against.
 *
 * This section used to be a conformance report — "twenty variants, measured
 * from the runtime-resolved token values rather than numbers copied into a
 * test". All true, and all addressed to an auditor or a contributor. The
 * person who opens Help looking for the accessibility section is usually the
 * person who needs it to work, and none of it told them a single thing they
 * could do: not which key skips the navigation, not where to turn the motion
 * off, not that there is a high-contrast world one keypress away.
 *
 * So every entry now names a control and what it does. The compliance claims
 * are not lost, they are just not the headline — they belong to the last card,
 * which is the one an auditor would have come for, and to the CI lanes that
 * actually hold them (e2e/themes.spec.ts, e2e/responsive.spec.ts).
 *
 * Keys are written the way the shortcuts table writes them, because they ARE
 * that table — a reader who tries `g` `h` from this paragraph must land on the
 * page the row below promises.
 */
const A11Y = [
  {
    title: "Skip past the navigation",
    body: "Press Tab as soon as a page loads: the first stop is a “Skip to content” link that jumps straight to the main region, past the header and the menu button. Everything after it follows the order the page reads in.",
  },
  {
    title: "Move around without a mouse",
    body: "Press ? for the full list of shortcuts. g then a letter jumps to a section — g d for the dashboard, g k for designs, g f for facilities, g h for this page. Esc closes any menu or dialog and returns you to the control that opened it.",
  },
  {
    title: "If a theme is hard to read",
    body: "Press m to switch between light and dark, and t to move to the next of the ten themes — Mono and Terminal are the plainest. Every theme is checked for text contrast in both light and dark before release, so none of them is the one that only half works.",
  },
  {
    title: "If motion is a problem",
    body: "Turn on “reduce motion” in your operating system’s accessibility settings and this app follows it: the loading mark stops animating, menus and dialogs appear without sliding, and nothing else moves on its own. Nothing here animates without being asked to.",
  },
  {
    title: "If text is too small",
    body: "Zoom with your browser (Ctrl or ⌘ with + and −) up to 200% and the layout reflows rather than clipping or scrolling sideways. Raising your browser’s default font size works too, and the charts and labels grow with it.",
  },
  {
    title: "With a screen reader",
    body: "Each page starts with one heading naming it, and panels are labelled regions you can jump between. The current page is marked in the menu. Icons are decorative and never carry meaning on their own — the words beside them say the same thing. Results of an action, such as a saved change or a failed request, are announced when they happen.",
  },
];

/**
 * A section heading that is also a destination. `scroll-mt` keeps the sticky
 * header from covering the target when a #fragment lands on it.
 */
function SectionHeading({
  id,
  children,
}: {
  id: string;
  children: React.ReactNode;
}) {
  return (
    <h2 id={id} className={cn(SECTION_LABEL, "group scroll-mt-20")}>
      {/*
        inline-flex + min-h-6 so the permalink clears the 24x24 WCAG 2.5.8
        minimum. The anchor wraps the whole heading, so its accessible name is
        the heading text and 2.5.8's inline exception does not apply — there is
        no surrounding non-target text constraining it. At section-label scale
        the line box was 21px, and the only thing holding it there was the type
        scale, which is the author's choice and therefore the author's problem.
      */}
      <a
        href={`#${id}`}
        className="inline-flex min-h-6 items-center no-underline hover:text-foreground"
      >
        {children}
        <span
          aria-hidden="true"
          className="ml-2 opacity-0 transition-opacity group-hover:opacity-60 group-focus-within:opacity-60"
        >
          #
        </span>
        <span className="sr-only"> — link to this section</span>
      </a>
    </h2>
  );
}

export function HelpView() {
  return (
    <div className="space-y-8">
      <PageHero title="Help" crumb="routes · shortcuts · accessibility" />

      <section aria-labelledby="h-routes" className="space-y-4">
        <SectionHeading id="h-routes">Where things are</SectionHeading>
        {[...NAV_GROUPS, ACCOUNT_GROUP].map((group) => (
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
        <SectionHeading id="h-keys">Keyboard shortcuts</SectionHeading>
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
        <SectionHeading id="h-a11y">Accessibility</SectionHeading>
        <div className="grid gap-4 sm:grid-cols-2">
          {A11Y.map((item) => (
            <div key={item.title} className={PANEL}>
              <h3 className={CARD_TITLE}>{item.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{item.body}</p>
            </div>
          ))}
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
