"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useAuth } from "../../context/AuthContext";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";

function RedirectUnless({
  children,
  allowed,
}: {
  children: ReactNode;
  allowed: boolean;
}) {
  const { signedIn, user, authError } = useAuth();
  const router = useRouter();

  // TanStack Query's isLoading is false while pending+idle (before fetch starts),
  // so wait on "a credential is set but whoami has not settled" instead.
  const settling = signedIn && !user && !authError;

  useEffect(() => {
    if (!settling && !allowed) router.replace("/");
  }, [settling, allowed, router]);

  if (settling) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner />
      </div>
    );
  }

  if (!allowed) return null;
  return <>{children}</>;
}

/** Redirect non-admins away from Settings. Waits for whoami when a token is set. */
export function RequireAdmin({ children }: { children: ReactNode }) {
  const { isAdmin } = useAuth();
  return <RedirectUnless allowed={isAdmin}>{children}</RedirectUnless>;
}

/** Settings a coordinator may open: invites and the member inventory. */
export function RequireCoordinator({ children }: { children: ReactNode }) {
  const { isAdmin, isCoordinator } = useAuth();
  return (
    <RedirectUnless allowed={isAdmin || isCoordinator}>
      {children}
    </RedirectUnless>
  );
}
