import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "@fontsource-variable/geist/index.css";
import "@/index.css";
import { Providers } from "./providers";
import { ThemeScript } from "./theme-script";
import {
  BRAND_DESCRIPTION,
  BRAND_GROUND_DARK,
  BRAND_GROUND_LIGHT,
  BRAND_NAME,
  BRAND_SHORT,
  BRAND_TITLE,
} from "./brand";

/**
 * Where this instance is served from, for the absolute URLs share cards need.
 *
 * OHM is self-hosted, so there is no single canonical origin to hard-code —
 * every deployment is somebody's own. Preview builds on Vercel get their own
 * hostname injected; anything else states it, and a local build falls back to
 * the dev server so `next build` never fails on an unset variable.
 */
function siteUrl(): URL {
  const explicit = process.env.NEXT_PUBLIC_SITE_URL;
  const vercel =
    process.env.VERCEL_PROJECT_PRODUCTION_URL || process.env.VERCEL_URL;
  if (explicit) return new URL(explicit);
  if (vercel) return new URL(`https://${vercel}`);
  return new URL("http://localhost:5173");
}

export const metadata: Metadata = {
  metadataBase: siteUrl(),
  // A detail page sets only its own subject; the template keeps the product
  // name in the tab without every page having to remember to say it.
  title: { default: BRAND_TITLE, template: `%s · ${BRAND_SHORT}` },
  description: BRAND_DESCRIPTION,
  applicationName: BRAND_NAME,
  // app/icon.svg is picked up by the file convention; naming it here as well
  // would emit the tag twice.
  appleWebApp: { capable: true, title: BRAND_SHORT, statusBarStyle: "default" },
  openGraph: {
    type: "website",
    siteName: BRAND_NAME,
    title: BRAND_TITLE,
    description: BRAND_DESCRIPTION,
  },
  twitter: {
    card: "summary_large_image",
    title: BRAND_TITLE,
    description: BRAND_DESCRIPTION,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // The browser paints its own chrome (mobile address bar, tab strip) before
  // the stylesheet lands, so this cannot be a token. Both polarities are
  // declared: one value would flash the wrong ground for half the visitors.
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: BRAND_GROUND_LIGHT },
    { media: "(prefers-color-scheme: dark)", color: BRAND_GROUND_DARK },
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/*
          First in the head, before anything else the parser has to fetch or
          resolve. It is a blocking script whose whole job is to finish before
          the first frame — see theme-script.tsx — so nothing belongs above it.
        */}
        <ThemeScript />
        {/*
          Written here rather than left to Next's `app/manifest.ts` convention,
          which emits the same tag without `crossorigin`. A manifest is fetched
          as a CORS request, so behind Vercel's deployment protection — where
          it is redirected to `vercel.com/sso-api` — the browser blocks the
          response and the install has no name and no icon. `use-credentials`
          sends the session cookie, the redirect resolves, and the fetch is a
          same-origin one on an unprotected deployment either way.
        */}
        <link
          rel="manifest"
          href="/manifest.webmanifest"
          crossOrigin="use-credentials"
        />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
