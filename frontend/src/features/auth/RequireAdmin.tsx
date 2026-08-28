"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useAuth } from "../../context/AuthContext";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";

/** Redirect non-admins away from Settings. Waits for whoami when a token is set. */
export function RequireAdmin({ children }: { children: ReactNode }) {
  const { token, isAdmin, user, authError } = useAuth();
  const router = useRouter();

  // TanStack Query's isLoading is false while pending+idle (before fetch starts),
  // so wait on "token set but whoami not settled" instead.
  const settling = Boolean(token) && !user && !authError;

  useEffect(() => {
    if (!settling && !isAdmin) router.replace("/");
  }, [settling, isAdmin, router]);

  if (settling) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner />
      </div>
    );
  }

  if (!isAdmin) {
    return null;
  }

  return <>{children}</>;
}
