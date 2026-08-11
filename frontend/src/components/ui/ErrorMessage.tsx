import { AlertTriangle } from "lucide-react";
import { PANEL_DANGER } from "./surface";
import { cn } from "@/lib/utils";

interface Props {
  error: Error | unknown;
  retry?: () => void;
  className?: string;
}

function errorText(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

export function ErrorMessage({ error, retry, className = "" }: Props) {
  return (
    <div className={cn(PANEL_DANGER, className)}>
      <div className="flex items-start gap-3">
        <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
        <div className="flex-1">
          <p className="text-sm font-medium text-destructive">Something went wrong</p>
          <p className="mt-1 text-sm text-destructive">{errorText(error)}</p>
          {retry && (
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
