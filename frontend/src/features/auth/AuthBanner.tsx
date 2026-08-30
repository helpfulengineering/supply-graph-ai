"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../context/AuthContext";
import { fetchSecurityPolicy } from "../../api/ohm/identity";

/**
 * Banner for 401/403 failures.
 *
 * It used to offer one way out — paste a key in Session — which assumed the
 * visitor already had one. Now that a node can mint identities, an anonymous
 * visitor's 401 is answerable on the spot, so registration leads when there is
 * no session at all. A signed-in visitor's 403 is not fixed by registering
 * again, so they keep the original pointer only.
 */
export function AuthBanner() {
  const { authFailure, clearAuthFailure, token } = useAuth();

  const policy = useQuery({
    queryKey: ["identity", "security-policy"],
    queryFn: fetchSecurityPolicy,
    staleTime: 5 * 60_000,
    retry: false,
    enabled: Boolean(authFailure) && !token,
  });

  if (!authFailure) return null;
  const canRegister = !token && policy.data?.open_registration === true;

  return (
    <div
      role="alert"
      className="border-b border-warning/30 bg-warning/10 px-6 py-3 text-sm text-warning"
    >
      <div className="mx-auto flex max-w-7xl items-start justify-between gap-4">
        <p>
          {authFailure}{" "}
          {canRegister && (
            <>
              <Link href="/register" className="font-medium underline">
                Register
              </Link>
              {" or "}
            </>
          )}
          <Link href="/settings/session" className="font-medium underline">
            Open Session
          </Link>
        </p>
        <button
          type="button"
          onClick={clearAuthFailure}
          className="shrink-0 text-warning underline"
          aria-label="Dismiss authentication message"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
