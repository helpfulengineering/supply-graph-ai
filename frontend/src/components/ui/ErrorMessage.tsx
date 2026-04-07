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
    <div className={`rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-950 ${className}`}>
      <div className="flex items-start gap-3">
        <span className="mt-0.5 text-red-500 dark:text-red-400" aria-hidden="true">⚠</span>
        <div className="flex-1">
          <p className="text-sm font-medium text-red-800 dark:text-red-300">Something went wrong</p>
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errorText(error)}</p>
          {retry && (
            <button
              onClick={retry}
              className="mt-3 rounded bg-red-100 px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-200 dark:bg-red-900 dark:text-red-300 dark:hover:bg-red-800 transition-colors"
            >
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
