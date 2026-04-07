interface Props {
  message?: string;
  className?: string;
}

export function LoadingSpinner({ message = "Loading…", className = "" }: Props) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 py-16 text-slate-500 dark:text-slate-400 ${className}`}>
      <svg
        className="h-8 w-8 animate-spin text-indigo-500"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>
      <span className="text-sm">{message}</span>
    </div>
  );
}
