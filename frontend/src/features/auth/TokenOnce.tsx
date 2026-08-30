"use client";

import { useId, type ReactNode } from "react";
import { PANEL_WARNING } from "../../components/ui/surface";
import { SECTION_TITLE } from "../../components/ui/typography";
import { FIELD_SM } from "../../components/ui/field";
import { useToast } from "../../components/ui/Toast";
import { cn } from "@/lib/utils";

/** Said on the toast rather than only in the panel, which the copy may scroll away from. */
const TOKEN_HINT = "Store it now — this instance will not show it again.";
const TOKEN_HINT_FAILED =
  "The token is still on screen. Select it and copy it by hand before leaving this page.";

/**
 * The one-time display of a credential.
 *
 * Two places mint tokens now — an admin creating a key, and a visitor
 * registering — and both are the worst moment in the app to get wrong: the
 * value exists exactly once, so a silent copy failure loses it for good. That
 * behaviour should not be maintained twice, which is what it was becoming.
 *
 * Hence the confirmed copy, and the loud report on a denied clipboard: a
 * visitor presses Copy, sees nothing, presses Done, and has lost the
 * credential is the failure this exists to prevent.
 */
export function TokenOnce({
  token,
  description,
  heading = "Copy this token now",
  onDismiss,
}: {
  token: string;
  /** Why this token matters here — the callers mean different things by it. */
  description: ReactNode;
  /** Overridden where the secret is not a token; the copy has to name it. */
  heading?: string;
  /** Omitted where the panel is the end of a flow and has nothing to dismiss to. */
  onDismiss?: () => void;
}) {
  const { showSuccess, showError } = useToast();
  // Two of these can be on screen at once (token and recovery code), so the
  // id that labels the dialog cannot be a constant — duplicate ids would point
  // both at the same heading.
  const headingId = useId();

  return (
    <div
      role="group"
      aria-labelledby={headingId}
      className={PANEL_WARNING}
    >
      <h2 id={headingId} className={cn(SECTION_TITLE, "text-warning")}>
        {heading}
      </h2>
      <p className="mt-1 text-sm text-warning">{description}</p>
      <pre className="mt-3 overflow-x-auto rounded-md bg-card p-3 font-mono text-xs">
        {token}
      </pre>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-accent"
          onClick={() =>
            navigator.clipboard.writeText(token).then(
              () => showSuccess("Token copied", { description: TOKEN_HINT }),
              (err: unknown) =>
                showError(err, { description: TOKEN_HINT_FAILED }),
            )
          }
        >
          Copy
        </button>
        {onDismiss && (
          <button type="button" className={FIELD_SM} onClick={onDismiss}>
            Done
          </button>
        )}
      </div>
    </div>
  );
}
