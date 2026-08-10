"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// The SPA's catch-all sent unknown paths home (App.tsx `*` route). Preserved
// as-is for the port; a designed 404 arrives with the chrome overhaul.
export default function NotFound() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/");
  }, [router]);
  return null;
}
