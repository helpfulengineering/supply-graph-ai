"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CircleUser } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { isActivePath } from "./nav";

/**
 * Who you are, in the chrome.
 *
 * Registration introduced a third class of visitor. Settings answered "who am
 * I" before, but Settings is admin-only, so a registered non-admin had no way
 * to see that they were signed in at all — and no way back to their own
 * records. This is the smallest thing that fixes both: one target, labelled
 * with the session, pointing at the page that is theirs.
 *
 * Square below `sm`, labelled from `sm` up, in the same idiom as Generate:
 * one text node either way (`sr-only`, not a second hidden copy), so the
 * accessible name is the same string at every width.
 */
export function SessionControl() {
  const { token, user } = useAuth();
  const pathname = usePathname() ?? "";
  const signedIn = Boolean(token);
  const href = signedIn ? "/account" : "/register";

  // Falls back to "Account" while whoami is still settling, so the control
  // never renders nameless and then reflows once the request lands.
  const label = signedIn ? (user?.name ?? "Account") : "Register";

  return (
    <Link
      href={href}
      aria-current={isActivePath(pathname, href) ? "page" : undefined}
      className="mr-1 flex h-11 w-11 items-center justify-center gap-2 rounded-md text-muted-foreground no-underline transition-colors hover:bg-muted hover:text-foreground sm:w-auto sm:px-3"
    >
      <CircleUser aria-hidden="true" className="h-5 w-5" />
      <span className="max-w-32 truncate text-sm font-medium sr-only sm:not-sr-only">
        {label}
      </span>
    </Link>
  );
}
