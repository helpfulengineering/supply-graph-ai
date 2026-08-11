"use client";

import { useEffect, useState, type ReactNode } from "react";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { queryClient, persistOptions } from "@/queryClient";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeContext } from "@/context/ThemeContext";
import { useDarkMode } from "@/hooks/useDarkMode";
import { useLookInUrl } from "@/hooks/useLookInUrl";
import { Layout } from "@/components/layout/Layout";
import { LogoLoader } from "@/components/ui/LogoLoader";
import { ToastProvider } from "@/components/ui/Toast";
import { TooltipProvider } from "@/components/ui/Tooltip";
import { installDemoFetch } from "@/lib/demo/demoFetch";
import { siteConfig } from "@/lib/site/config";

/**
 * The client provider stack, mounted once by the root layout.
 *
 * Rendering is gated on mount: the server ships the same empty shell the Vite
 * build did, and the app renders client-side exactly as before the migration.
 * This keeps sessionStorage-derived state (API key, color scheme, query cache)
 * out of server markup so there is nothing to mismatch during hydration.
 * Server rendering for public routes is a deliberate follow-up, not part of
 * the zero-feature-change port.
 */
// Demo mode swaps the data source at the fetch boundary. Installed here,
// before the gated render mounts anything that can issue a query, so no
// request escapes to the network first and no component ever learns the
// source changed.
installDemoFetch();

// Publish the site-layer posture on the document, so anything observing the
// app (tests, an operator with devtools) reads what the SERVER was built with
// rather than inferring it. Reading process.env in a test reads the runner's
// environment, which diverges the moment a running dev server is reused.
if (typeof document !== "undefined") {
  document.documentElement.dataset.siteLayer = siteConfig.enabled
    ? "on"
    : "off";
}

export function Providers({ children }: { children: ReactNode }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
    // Next's route announcer adds a permanent role="alert" live region (inside
    // a shadow root, out of CSS reach). The react-router app had no announcer,
    // and the e2e suite asserts a single-alert contract — hide it for parity.
    // The chrome overhaul owns reintroducing route announcements deliberately.
    // It mounts after this effect, so watch until it appears.
    const hide = () => {
      const host = document.querySelector("next-route-announcer");
      if (host) host.setAttribute("aria-hidden", "true");
      return Boolean(host);
    };
    if (hide()) return;
    const observer = new MutationObserver(() => {
      if (hide()) observer.disconnect();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  // Until the effect above runs, this is the entire document.
  //
  // It used to be `null`, which is a defensible thing to render — nothing here
  // can be server-rendered honestly — but not a defensible thing to SHOW. On a
  // cold load over a slow connection the visitor got a blank page for as long
  // as the bundle took, with no way to tell a loading app from a broken one.
  // The mark, animating, is the smallest true statement available: the app
  // exists and is on its way.
  if (!mounted) return <BootLoader />;
  return <MountedProviders>{children}</MountedProviders>;
}

/**
 * The first frame, before any provider exists.
 *
 * Rendered by the server and by the first client render alike, so there is
 * nothing here for hydration to disagree about — no stored theme, no session,
 * no query cache, which is the whole reason the gate exists.
 *
 * It carries the live region rather than nesting one inside `LoadingState`,
 * because at this point there is no Layout, no <main>, and no other text on
 * the page for a screen reader to reach.
 */
function BootLoader() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex min-h-screen flex-col items-center justify-center gap-3 text-muted-foreground"
    >
      <LogoLoader className="h-12 w-12" />
      <span className="text-sm">Loading Open Hardware Manager…</span>
    </div>
  );
}

function MountedProviders({ children }: { children: ReactNode }) {
  const theme = useDarkMode();
  useLookInUrl(theme.theme, theme.isDark);

  return (
    <ThemeContext.Provider value={theme}>
      <PersistQueryClientProvider
        client={queryClient}
        persistOptions={persistOptions}
      >
        <AuthProvider>
          <TooltipProvider>
            {/* Inside the query client, so a toast fired from a mutation's
                onError has one; outside Layout, so its viewport is a sibling
                of the page rather than a child of <main> — a fixed element
                inside the scroll container inherits its clipping. */}
            <ToastProvider>
              <Layout>{children}</Layout>
            </ToastProvider>
          </TooltipProvider>
        </AuthProvider>
      </PersistQueryClientProvider>
    </ThemeContext.Provider>
  );
}
