import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../../context/AuthContext";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";

/** Redirect non-admins away from Settings. Waits for whoami when a token is set. */
export function RequireAdmin({ children }: { children: ReactNode }) {
  const { token, isAdmin, user, authError } = useAuth();

  // TanStack Query's isLoading is false while pending+idle (before fetch starts),
  // so wait on "token set but whoami not settled" instead.
  if (token && !user && !authError) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner />
      </div>
    );
  }

  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
