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
    <div className={`rounded-lg border border-destructive bg-destructive/10 p-4 ${className}`}>
      <div className="flex items-start gap-3">
        <span className="mt-0.5 text-destructive" aria-hidden="true">⚠</span>
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
