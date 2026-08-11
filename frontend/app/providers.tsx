"use client";

import { useEffect, useState, type ReactNode } from "react";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { queryClient, persistOptions } from "@/queryClient";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeContext } from "@/context/ThemeContext";
import { useDarkMode } from "@/hooks/useDarkMode";
import { Layout } from "@/components/layout/Layout";
import { installDemoFetch } from "@/lib/demo/demoFetch";

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

  if (!mounted) return null;
  return <MountedProviders>{children}</MountedProviders>;
}

function MountedProviders({ children }: { children: ReactNode }) {
  const theme = useDarkMode();

  return (
    <ThemeContext.Provider value={theme}>
      <PersistQueryClientProvider
        client={queryClient}
        persistOptions={persistOptions}
      >
        <AuthProvider>
          <Layout>{children}</Layout>
        </AuthProvider>
      </PersistQueryClientProvider>
    </ThemeContext.Provider>
  );
}
