"use client";

import Link from "next/link";
import { navEntryFor } from "../../components/layout/nav";

interface Step {
  n: number;
  title: string;
  body: string;
  /** Where the CTA goes. */
  to: string;
  /** Route to take the icon from, when it is not where the CTA goes. */
  icon?: string;
  cta: string;
}

const STEPS: Step[] = [
  {
    n: 1,
    title: "Find a design",
    body: "Browse open hardware designs by category, process, and capability.",
    to: "/okh",
    cta: "Browse designs",
  },
  {
    n: 2,
    title: "Match it to facilities",
    body: "Run a domain-aware match to see which facilities can produce it, ranked by confidence.",
    to: "/match",
    cta: "Run a match",
  },
  {
    n: 3,
    title: "See the supply tree",
    body: "Each match opens an interactive supply tree — production plan, facility distribution, dependencies — which you can download.",
    // The step is about the supply tree, but a tree is a match result and has
    // no browsable entry — so the link goes to the match that produces one
    // while the icon names what you are being sent to see.
    to: "/match",
    icon: "/visualization",
    cta: "Run a match",
  },
];

/**
 * Onboarding guidance — the "how to use OHM" path, not a duplicate of the nav.
 *
 * Each step wears the icon of the destination it sends you to, resolved from
 * the sitemap rather than picked here. The step number says where you are in
 * the sequence; the glyph says which part of the app you are about to be in,
 * and it is the same glyph you will meet in the menu and again in that page's
 * hero.
 */
export function GettingStarted() {
  return (
    <section aria-labelledby="getting-started-heading">
      <h2
        id="getting-started-heading"
        className="mb-3 text-lg font-semibold text-foreground"
      >
        Getting started
      </h2>
      <ol className="space-y-2.5">
        {STEPS.map((s) => {
          const target = navEntryFor(s.icon ?? s.to);
          const Icon = target?.entry.icon;
          return (
            <li
              key={s.n}
              className="flex gap-3 rounded-xl border border-border bg-card p-3.5"
            >
              <span
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-on-accent"
                aria-hidden="true"
              >
                {s.n}
              </span>
              <div className="min-w-0">
                <p className="flex items-center gap-2 font-medium text-foreground">
                  {Icon && (
                    <Icon
                      aria-hidden="true"
                      className={`h-4 w-4 shrink-0 ${target.group.accent}`}
                    />
                  )}
                  {s.title}
                </p>
                <p className="mt-0.5 text-sm text-muted-foreground">{s.body}</p>
                <Link
                  href={s.to}
                  className="mt-1.5 inline-block text-sm font-medium text-primary-ink hover:underline"
                >
                  {s.cta} →
                </Link>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
