"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { siteConfig } from "./config";
import { EVENTS } from "./events";
import { track } from "./stack";

/**
 * Records one page view per route the reader actually lands on.
 *
 * THIS REPLACES A MOUNT EFFECT THAT COULD NOT WORK. `page_view` used to fire
 * from `useSiteLayer`, on mount, with an empty dependency list. Two things
 * followed, and both made the telemetry describe something other than usage:
 *
 * 1. NAVIGATION WAS INVISIBLE. The hook's only always-mounted caller is the
 *    nav drawer, which lives in the layout and therefore mounts once per hard
 *    load. This is a client-routed app: moving from the dashboard to matching
 *    to a facility never remounts the layout, so a whole session recorded a
 *    single view of whichever page was entered first. The `page` column was
 *    effectively a landing-page column.
 * 2. MISSION CONTROL DOUBLE-COUNTED. It calls `useSiteLayer` for its own
 *    state, so on that route two components ran the same mount effect and the
 *    operator page inflated its own numbers — the one page whose numbers an
 *    operator reads.
 *
 * Mounting once, above the routed subtree, and keying on `usePathname` fixes
 * both: the effect belongs to the router's idea of location rather than to any
 * component's lifetime, and there is exactly one of it.
 *
 * The ref guard is for React's development double-invoke and for the repeated
 * renders a single navigation can produce; a path is recorded once until it
 * changes. Returning to a page you were just on is a real second view, which
 * is why the guard holds the last path rather than a set of every path seen.
 */
export function RouteTelemetry() {
  const pathname = usePathname();
  const last = useRef<string | null>(null);

  useEffect(() => {
    if (!siteConfig.enabled || !pathname) return;
    if (last.current === pathname) return;
    last.current = pathname;
    // `page` comes from the client's own location inside track(), so the path
    // is not passed here — one source for it, and it is the one the RPC reads.
    track(EVENTS.pageView);
  }, [pathname]);

  return null;
}
