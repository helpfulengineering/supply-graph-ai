import { Link } from "react-router-dom";

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
    title: "Explore the supply tree",
    body: "Inspect the production plan, facility distribution, and dependencies for a solution.",
    to: "/solutions",
    cta: "View solutions",
  },
];

/** Onboarding guidance — the "how to use OHM" path, not a duplicate of the nav. */
export function GettingStarted() {
  return (
    <section aria-labelledby="getting-started-heading">
      <h2 id="getting-started-heading" className="mb-3 text-lg font-semibold text-foreground">
        Getting started
      </h2>
      <ol className="space-y-3">
        {STEPS.map((s) => (
          <li
            key={s.n}
            className="flex gap-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900"
          >
            <span
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-sm font-semibold text-white"
              aria-hidden="true"
            >
              {s.n}
            </span>
            <div className="min-w-0">
              <p className="font-medium text-slate-800 dark:text-slate-100">{s.title}</p>
              <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-400">{s.body}</p>
              <Link
                to={s.to}
                className="mt-1.5 inline-block text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
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
