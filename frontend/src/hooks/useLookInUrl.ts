"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import type { ThemeSlug } from "./useDarkMode";

/**
 * Keeps the current look in the address bar.
 *
 * `?theme=` and `?mode=` have been read on arrival for a while, but only ever
 * written by the drawer's "copy link with this look" — so the obvious way to
 * share a page, copying the URL, was the one way that lost it. The look is
 * part of what you are looking at; the address should say so without being
 * asked.
 *
 * replaceState, not the router: this is not a navigation. Pushing would put an
 * entry between the visitor and the page they came from every time they
 * changed theme, and routing would re-render the tree to change nothing.
 *
 * Re-asserted on pathname changes because a client navigation carries only the
 * href the link named. Same-route query rewrites keep it themselves — see
 * lib/urlState, which is why filter writers merge instead of rebuilding.
 */
export function useLookInUrl(theme: ThemeSlug, isDark: boolean): void {
  const pathname = usePathname();

  useEffect(() => {
    // Deferred a frame. Next patches the history methods and routes the call
    // through its router, which throws "Router action dispatched before
    // initialization" if it arrives while the router is still coming up — and
    // this effect runs from the provider, which is as early as that gets.
    // Waiting a frame costs nothing: the parameter is a record of the current
    // look, not something the first paint depends on.
    const frame = requestAnimationFrame(() => {
      const mode = isDark ? "dark" : "light";
      const url = new URL(window.location.href);
      if (
        url.searchParams.get("theme") === theme &&
        url.searchParams.get("mode") === mode
      ) {
        return;
      }
      url.searchParams.set("theme", theme);
      url.searchParams.set("mode", mode);
      window.history.replaceState(window.history.state, "", url);
    });
    return () => cancelAnimationFrame(frame);
  }, [theme, isDark, pathname]);
}
