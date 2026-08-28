import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained node server for the container image (replaces nginx).
  // Standalone is for the Docker image: it emits a self-contained server the
  // runtime stage copies, replacing what nginx used to serve. Vercel does its
  // own dependency tracing and its post-build step reads
  // .next/next-server.js.nft.json, which standalone relocates — the build then
  // fails with ENOENT there. So the flag is for our own image only; on Vercel
  // the default output is correct.
  output: process.env.VERCEL ? undefined : "standalone",
  // Trailing slashes are policy-per-surface (docs keep them, app routes drop
  // them); proxy.ts owns the split, so the global redirect is off.
  skipTrailingSlashRedirect: true,
};

export default nextConfig;
