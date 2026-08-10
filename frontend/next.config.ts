import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained node server for the container image (replaces nginx).
  output: "standalone",
  // Trailing slashes are policy-per-surface (docs keep them, app routes drop
  // them); proxy.ts owns the split, so the global redirect is off.
  skipTrailingSlashRedirect: true,
};

export default nextConfig;
