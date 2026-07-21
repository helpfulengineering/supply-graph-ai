import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

/** Banner for 401/403 failures — points admins at Settings. */
export function AuthBanner() {
  const { authFailure, clearAuthFailure, isAdmin } = useAuth();
  if (!authFailure) return null;

  return (
    <div
      role="alert"
      className="border-b border-amber-200 bg-amber-50 px-6 py-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100"
    >
      <div className="mx-auto flex max-w-7xl items-start justify-between gap-4">
        <p>
          {authFailure}
          {isAdmin && (
            <>
              {" "}
              <Link to="/settings/session" className="font-medium underline">
                Open Settings
              </Link>
            </>
          )}
        </p>
        <button
          type="button"
          onClick={clearAuthFailure}
          className="shrink-0 text-amber-800 underline dark:text-amber-200"
          aria-label="Dismiss authentication message"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
