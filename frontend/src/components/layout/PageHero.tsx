import type { ReactNode } from "react";

interface PageHeroProps {
  title: ReactNode;
  /** Mono role line beside the title — the admin page's "telemetry · visitors" idiom. */
  crumb?: string;
  actions?: ReactNode;
}

/**
 * The page hero, matched to ohm.thetechmargin.com/admin: a concise baseline
 * row — h1 at --ttm-fs-h3 weight 600, a mono crumb — closed by the iridescent
 * rule. The site bar above stays pure chrome; this is where a page states its
 * identity, so the brand rule lives here.
 *
 * The rule is static: an animated shimmer would leave a permanently-running
 * animation, and the axe helper waits for animations to settle before every
 * scan — each of the 20 theme-matrix scans would eat the full timeout.
 */
export function PageHero({ title, crumb, actions }: PageHeroProps) {
  return (
    <header className="mb-3">
      <div className="flex flex-wrap items-baseline gap-x-3">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">
          {title}
        </h1>
        {crumb && (
          <span className="font-mono text-xs text-muted-foreground">{crumb}</span>
        )}
        {actions && <span className="ml-auto flex items-center gap-2">{actions}</span>}
      </div>
      <div
        aria-hidden="true"
        className="mt-1.5 h-px w-full rounded-full"
        style={{
          background:
            "linear-gradient(120deg, var(--ttm-irid-a), var(--ttm-irid-b), var(--ttm-irid-c), var(--ttm-irid-d), var(--ttm-irid-e))",
        }}
      />
    </header>
  );
}
