"use client";

import Link from "next/link";
import { PANEL } from "../../components/ui/surface";
import { cn } from "@/lib/utils";

const STEPS = [
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
    to: "/match",
    cta: "Run a match",
  },
];

/** Onboarding guidance — the "how to use OHM" path, not a duplicate of the nav. */
export function GettingStarted() {
  return (
    <section aria-labelledby="getting-started-heading">
      <h2
        id="getting-started-heading"
        className="mb-3 text-lg font-semibold text-foreground"
      >
        Getting started
      </h2>
      <ol className="space-y-3">
        {STEPS.map((s) => (
          <li key={s.n} className={cn(PANEL, "flex gap-3")}>
            <span
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-on-accent"
              aria-hidden="true"
            >
              {s.n}
            </span>
            <div className="min-w-0">
              <p className="font-medium text-foreground">{s.title}</p>
              <p className="mt-0.5 text-sm text-muted-foreground">{s.body}</p>
              <Link
                href={s.to}
                className="mt-1.5 inline-block text-sm font-medium text-primary-ink hover:underline"
              >
                {s.cta} →
              </Link>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
