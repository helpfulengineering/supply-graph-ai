"use client";

import {
  BRAND_GROUND_DARK,
  BRAND_GROUND_LIGHT,
  BRAND_INK_DARK,
  BRAND_INK_LIGHT,
  BRAND_INK_MUTED_DARK,
  BRAND_INK_MUTED_LIGHT,
  BRAND_RAMP_DARK,
  BRAND_SHORT,
} from "./brand";
import {
  MARK_EDGES,
  MARK_NODES,
  MARK_OUTLINE,
  MARK_STROKE_WIDTH,
  MARK_VIEWBOX,
} from "@/components/layout/mark";

/**
 * The net under the net.
 *
 * `error.tsx` renders inside the root layout, which means it cannot catch a
 * failure in the root layout itself or in the provider stack it mounts — a
 * broken theme script, a provider throwing on a corrupt persisted query cache.
 * When that happens Next replaces the entire document, and without this file
 * what replaces it is an unstyled "Application error" on a white page.
 *
 * This file therefore renders its own <html> and <body>, and — the constraint
 * that shapes everything below — the app's global stylesheet is NOT loaded
 * here. There are no Tailwind utilities, no token variables, no `var(--ttm-*)`
 * to resolve, and no `data-ttm-theme` to honour, because the element that
 * would carry it is the one being replaced.
 *
 * So this is the second legitimate consumer of app/brand.ts, for exactly the
 * reason the favicon is the first: it is painted outside the cascade the token
 * layer lives in. Colour arrives as baked constants that src/test/brand.test.ts
 * already pins to tokens.css, and the OS `prefers-color-scheme` is the only
 * theme signal available — the app's chosen world is unreachable from here.
 *
 * Geometry still comes from mark.ts. A hand-drawn mark on the one page nobody
 * looks at until it matters is precisely how a mark drifts.
 */
export default function GlobalError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0 }}>
        {/* React 19 hoists this; `metadata` is not available in a client
            component, and a document with no title shows the raw URL in the
            tab at the exact moment a person is trying to describe what they
            were looking at. */}
        <title>{`Something went wrong · ${BRAND_SHORT}`}</title>
        <style>{CSS}</style>

        <main className="wrap">
          <svg
            className="mark"
            viewBox={`0 0 ${MARK_VIEWBOX} ${MARK_VIEWBOX}`}
            aria-hidden="true"
            fill="none"
          >
            <defs>
              <linearGradient id="ohm-global-error" x1="0" y1="0" x2="1" y2="1">
                {/* The favicon's stops, for the reason the favicon bakes them:
                    no stylesheet is loaded, so the live ramp cannot resolve. */}
                <stop offset="0%" stopColor={BRAND_RAMP_DARK[0]} />
                <stop offset="30%" stopColor={BRAND_RAMP_DARK[1]} />
                <stop offset="60%" stopColor={BRAND_RAMP_DARK[2]} />
                <stop offset="100%" stopColor={BRAND_RAMP_DARK[4]} />
              </linearGradient>
            </defs>
            <path
              d={MARK_OUTLINE}
              stroke="url(#ohm-global-error)"
              strokeWidth={MARK_STROKE_WIDTH}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d={MARK_EDGES}
              stroke="url(#ohm-global-error)"
              strokeWidth={MARK_STROKE_WIDTH}
              strokeLinecap="round"
            />
            {MARK_NODES.map((node) => (
              <circle
                key={`${node.cx},${node.cy}`}
                cx={node.cx}
                cy={node.cy}
                r={node.r}
                fill="url(#ohm-global-error)"
              />
            ))}
          </svg>

          <h1>{BRAND_SHORT} could not start</h1>
          <p>
            Something failed before the app finished loading, so this page is
            all there is right now. Reloading clears most causes; if it does
            not, the instance itself may be having trouble.
          </p>

          <button type="button" onClick={() => retry()}>
            Reload the app
          </button>

          {error.digest && (
            <p className="digest">
              Reference for the logs: <code>{error.digest}</code>
            </p>
          )}
        </main>
      </body>
    </html>
  );
}

/**
 * Written as a string rather than as style props because of the media query:
 * `prefers-color-scheme` cannot be expressed inline, and this document has no
 * other way to know which ground it is being painted on. Light is the default
 * and dark is the override, matching the app's own default world.
 */
const CSS = `
  .wrap {
    box-sizing: border-box;
    min-height: 100vh;
    margin: 0 auto;
    padding: 3rem 1.5rem;
    max-width: 34rem;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    justify-content: center;
    gap: 1rem;
    font-family: ui-sans-serif, system-ui, sans-serif;
    background: ${BRAND_GROUND_LIGHT};
    color: ${BRAND_INK_LIGHT};
  }
  .mark { width: 3rem; height: 3rem; }
  h1 { margin: 0; font-size: 1.5rem; line-height: 1.2; font-weight: 600; }
  p { margin: 0; font-size: 0.9375rem; line-height: 1.6; color: ${BRAND_INK_MUTED_LIGHT}; }
  code { font-family: ui-monospace, monospace; }
  .digest { font-size: 0.8125rem; }
  button {
    /* 44px: the same floor the app's own dead-end pages hold their controls
       to. This is the only control on the page. */
    min-height: 2.75rem;
    padding: 0 1rem;
    border: 0;
    border-radius: 0.5rem;
    font: inherit;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    background: ${BRAND_INK_LIGHT};
    color: ${BRAND_GROUND_LIGHT};
  }
  button:hover { opacity: 0.9; }
  @media (prefers-color-scheme: dark) {
    .wrap { background: ${BRAND_GROUND_DARK}; color: ${BRAND_INK_DARK}; }
    p { color: ${BRAND_INK_MUTED_DARK}; }
    button { background: ${BRAND_INK_DARK}; color: ${BRAND_GROUND_DARK}; }
  }
`;
