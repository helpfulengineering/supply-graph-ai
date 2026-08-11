"use client";

import Link from "next/link";
import { useAuth } from "../../context/AuthContext";

/** Banner for 401/403 failures — points at Session to paste a key. */
export function AuthBanner() {
  const { authFailure, clearAuthFailure } = useAuth();
  if (!authFailure) return null;

  return (
    <div
      role="alert"
      className="border-b border-warning/30 bg-warning/10 px-6 py-3 text-sm text-warning"
    >
      <div className="mx-auto flex max-w-7xl items-start justify-between gap-4">
        <p>
          {authFailure}{" "}
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
