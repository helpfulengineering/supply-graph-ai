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
  // No runtime image optimisation, declared rather than left to chance.
  //
  // Next pulls `sharp` into the standalone output as an optional dependency,
  // and sharp ships a platform-specific .node binary. The build stage is now
  // pinned to BUILDPLATFORM (see frontend/Dockerfile), so that binary is the
  // BUILD architecture's — harmless only for as long as nothing loads it.
  //
  // Nothing does: next/image appears in exactly two files, both of which are
  // comments noting it has no meaning inside an ImageResponse, and both use a
  // plain <img>. Saying so here turns that from an accident into a contract. If
  // a future change wants next/image, it needs sharp for the TARGET
  // architecture, which means installing it in the runtime stage — not simply
  // deleting this line.
  images: { unoptimized: true },
  // Trailing slashes are policy-per-surface (docs keep them, app routes drop
  // them); proxy.ts owns the split, so the global redirect is off.
  skipTrailingSlashRedirect: true,
};

export default nextConfig;
