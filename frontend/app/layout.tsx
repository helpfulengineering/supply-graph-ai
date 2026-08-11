import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "@fontsource-variable/geist/index.css";
import "@/index.css";
import { Providers } from "./providers";
import { ThemeScript } from "./theme-script";

export const metadata: Metadata = {
  title: "OHM — Open Hardware Matchmaker",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
