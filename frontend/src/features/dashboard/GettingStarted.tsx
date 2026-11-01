"use client";

import Link from "next/link";
import { navEntryFor } from "../../components/layout/nav";
import { SECTION_LABEL, SECTION_TITLE } from "../../components/ui/typography";
import { cn } from "@/lib/utils";
import { PANEL } from "../../components/ui/surface";

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
    title: "Take the list with you",
    body: "Select the workshops you want and export their contact details as a spreadsheet. Coordination happens outside OHM — this is how a result leaves it.",
    // Same destination as step 2: the export lives on the match results, which
    // is where you are once you have an answer worth acting on.
    to: "/match",
    cta: "Run a match",
  },
];

/**
 * The other way in (#561): a first-time designer read the three steps above as
 * the whole of OHM and had to discover that Generate is how a design gets in.
 */
const DESIGNER_STEP: Step = {
  n: 1,
  title: "Add your design",
  body: "Point OHM at your repository and it reads the design into a record you review and correct. You don't install anything: you become a member of this node.",
  to: "/okh/generate",
  cta: "Add your design",
};

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
      <h2 id="getting-started-heading" className={cn(SECTION_TITLE, "mb-3")}>
        Getting started
      </h2>
      <h3 className={cn(SECTION_LABEL, "mb-2")}>
        Build something
      </h3>
      <ol className="space-y-2.5">
        {STEPS.map((s) => (
          <StepCard key={s.n} step={s} />
        ))}
      </ol>
      <h3 className={cn(SECTION_LABEL, "mb-2 mt-4")}>
        Share your design
      </h3>
      <ol>
        <StepCard step={DESIGNER_STEP}>
          <Link
            href="/docs/guides/for-designers/"
            className="ml-4 mt-1.5 inline-block text-sm text-muted-foreground underline"
          >
            For designers
          </Link>
        </StepCard>
      </ol>
    </section>
  );
}

function StepCard({
  step: s,
  children,
}: {
  step: Step;
  children?: React.ReactNode;
}) {
  const target = navEntryFor(s.icon ?? s.to);
  const Icon = target?.entry.icon;
  return (
    <li className={cn(PANEL, "flex gap-3 p-3.5")}>
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
        {children}
      </div>
    </li>
  );
}
