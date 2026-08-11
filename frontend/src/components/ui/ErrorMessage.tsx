import { AlertTriangle } from "lucide-react";
import { PANEL_DANGER } from "./surface";
import { userFacingError } from "@/lib/userMessage";
import { cn } from "@/lib/utils";

interface Props {
  error: Error | unknown;
  retry?: () => void;
  className?: string;
}

/**
 * A failure, in a panel, said in the user's language.
 *
 * The heading used to be a fixed "Something went wrong" over whatever
 * `err.message` happened to be, which meant a rate limit, a deleted record and
 * a dropped connection all arrived under one word and were told apart only by
 * whatever text the API or the browser had put in the exception. The wording
 * now comes from `userFacingError`, so this component renders a message rather
 * than composing one — and the same failure reads the same here, on the
 * route-level error page, and anywhere else that maps an error.
 */
export function ErrorMessage({ error, retry, className = "" }: Props) {
  const message = userFacingError(error);
  return (
    <div className={cn(PANEL_DANGER, className)}>
      <div className="flex items-start gap-3">
        <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
        <div className="flex-1">
          <p className="text-sm font-medium text-destructive">{message.title}</p>
          <p className="mt-1 text-sm text-destructive">{message.body}</p>
          {message.requestId && (
            // The one string an operator needs to find this in the logs, and
            // the one thing a user cannot be expected to reconstruct.
            <p className="mt-1 font-mono text-caption text-muted-foreground">
              request {message.requestId}
            </p>
          )}
          {/* A retry control is offered only where the caller wired one AND a
              second attempt could actually succeed: a button that re-runs a
              403 teaches people that buttons here do nothing. */}
          {retry && message.retryable && (
            <button
              onClick={retry}
              className="mt-3 rounded bg-destructive/10 px-3 py-1 text-xs font-medium text-destructive hover:bg-destructive/20 transition-colors"
            >
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
